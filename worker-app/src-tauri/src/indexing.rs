use crate::types::{FileEntry, Manifest, RepoIndex, RouteEntry, SKIP_DIRS, SOURCE_SUFFIXES, MANIFEST_NAMES};
use ignore::WalkBuilder;
use std::path::Path;

pub async fn index_repo<P: AsRef<Path>>(repo_dir: P) -> RepoIndex {
    let repo_dir = repo_dir.as_ref();
    let mut inventory: Vec<FileEntry> = Vec::new();
    let mut manifests: Vec<Manifest> = Vec::new();
    let mut route_map: Vec<RouteEntry> = Vec::new();
    let mut todos: Vec<String> = Vec::new();

    let walker = WalkBuilder::new(repo_dir)
        .standard_filters(true)
        .build();

    for result in walker {
        let entry = match result {
            Ok(e) => e,
            Err(_) => continue,
        };
        if !entry.file_type().map(|ft| ft.is_file()).unwrap_or(false) {
            continue;
        }
        let path = entry.path();
        let rel = path.strip_prefix(repo_dir).unwrap_or(path);
        let rel_str = rel.to_string_lossy().replace('\\', "/");
        if rel.components().any(|c| {
            let name = c.as_os_str().to_string_lossy();
            SKIP_DIRS.contains(&name.as_ref())
        }) {
            continue;
        }

        let metadata = match std::fs::metadata(path) {
            Ok(m) => m,
            Err(_) => continue,
        };
        let size = metadata.len();
        let kind = kind(path);

        inventory.push(FileEntry {
            path: rel_str.clone(),
            size,
            kind,
        });

        if MANIFEST_NAMES.contains(&path.file_name().and_then(|n| n.to_str()).unwrap_or("")) {
            let content = read_file(path, 24000);
            manifests.push(Manifest {
                path: rel_str.clone(),
                content,
            });
        }

        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
            if SOURCE_SUFFIXES.contains(&format!(".{}", ext).as_str()) && size < 250_000 {
                let content = read_file(path, 60_000);
                for line in content.lines() {
                    if line.contains("TODO") || line.contains("FIXME") {
                        todos.push(format!("{}: {}", rel_str, &line[..line.len().min(180)]));
                    }
                    if line.contains("@app.") || line.contains("APIRouter") || line.contains("router.") {
                        route_map.push(RouteEntry {
                            path: rel_str.clone(),
                            line: line[..line.len().min(220)].to_string(),
                        });
                    }
                }
            }
        }
    }

    RepoIndex {
        file_inventory: inventory,
        manifests: manifests.clone(),
        route_map: route_map.into_iter().take(200).collect(),
        test_commands: detect_tests(&manifests),
        risks: Vec::new(),
        todos: todos.into_iter().take(200).collect(),
        searchable_chunks: Vec::new(),
        architecture_summary: String::new(),
    }
}

fn kind(path: &Path) -> String {
    let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
    if MANIFEST_NAMES.contains(&name) {
        return "manifest".to_string();
    }
    if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
        let ext_lower = ext.to_lowercase();
        if SOURCE_SUFFIXES.contains(&format!(".{}", ext_lower).as_str()) {
            return "source".to_string();
        }
        if ["md", "txt", "rst"].contains(&ext_lower.as_str()) {
            return "doc".to_string();
        }
    }
    "asset".to_string()
}

fn read_file(path: &Path, limit: usize) -> String {
    match std::fs::read_to_string(path) {
        Ok(content) => content.chars().take(limit).collect(),
        Err(_) => String::new(),
    }
}

fn detect_tests(manifests: &[Manifest]) -> Vec<String> {
    let mut commands: Vec<String> = Vec::new();
    for manifest in manifests {
        if manifest.path.ends_with("package.json") {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&manifest.content) {
                if let Some(scripts) = parsed.get("scripts").and_then(|s| s.as_object()) {
                    if scripts.contains_key("test") {
                        commands.push("npm test".to_string());
                    }
                    if scripts.contains_key("build") {
                        commands.push("npm run build".to_string());
                    }
                }
            }
        }
        if manifest.path.ends_with("pyproject.toml") {
            commands.push("python -m pytest".to_string());
        }
    }
    commands
}
