# Graph Report - .  (2026-05-02)

## Corpus Check
- 16 files · ~5,135 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 75 nodes · 123 edges · 10 communities detected
- Extraction: 68% EXTRACTED · 32% INFERRED · 0% AMBIGUOUS · INFERRED: 39 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]

## God Nodes (most connected - your core abstractions)
1. `Run()` - 16 edges
2. `run()` - 9 edges
3. `Run()` - 8 edges
4. `LoadLocalConfig()` - 7 edges
5. `ConfigFilePath()` - 7 edges
6. `runSelfBuild()` - 6 edges
7. `StateDirs()` - 6 edges
8. `SaveLocalConfig()` - 5 edges
9. `Run()` - 5 edges
10. `WriteSampleTask()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Run()` --calls--> `RunDir()`  [INFERRED]
  internal\status\status.go → internal\config\paths.go
- `TestRunReportsUninitialized()` --calls--> `Run()`  [INFERRED]
  internal\status\status_test.go → internal\status\status.go
- `run()` --calls--> `Info()`  [INFERRED]
  cmd\karkhana\main.go → internal\version\version.go
- `runInstall()` --calls--> `ValidateMode()`  [INFERRED]
  cmd\karkhana\main.go → internal\install\mode.go
- `runSelfBuild()` --calls--> `ConfigFilePath()`  [INFERRED]
  cmd\karkhana\main.go → internal\config\paths.go

## Communities

### Community 0 - "Community 0"
Cohesion: 0.19
Nodes (12): LocalConfig, ensureStateDirs(), newNodeID(), resolvePath(), Run(), LoadLocalConfig(), SaveLocalConfig(), TestSaveAndLoadLocalConfig() (+4 more)

### Community 1 - "Community 1"
Cohesion: 0.31
Nodes (11): isHelpArg(), main(), printUsage(), run(), runDoctor(), runInit(), runInstall(), runSelfBuild() (+3 more)

### Community 2 - "Community 2"
Cohesion: 0.29
Nodes (8): OpenCode, Payload, Task, GenerateSampleTask(), MarshalSampleTask(), TestGenerateSampleTaskIncludesBranchesAndLocalConfig(), TestMarshalSampleTaskIsDeterministic(), WriteSampleTask()

### Community 3 - "Community 3"
Cohesion: 0.36
Nodes (6): ConfigFilePath(), fallbackHomeDir(), RunDir(), TestConfigFilePath(), UserConfigDir(), UserDataDir()

### Community 4 - "Community 4"
Cohesion: 0.33
Nodes (5): countFiles(), DirStatus, inspectDir(), Options, Result

### Community 5 - "Community 5"
Cohesion: 0.53
Nodes (5): TestRunCapturesOpenCodeVersion(), TestRunWarnsWhenOpenCodeMissing(), TestRunWarnsWhenOpenCodeVersionFailsButContinues(), TestRunWarnsWhenWorkingDirFails(), Run()

### Community 6 - "Community 6"
Cohesion: 0.5
Nodes (4): commandVersion(), Options, Result, Run()

### Community 7 - "Community 7"
Cohesion: 0.5
Nodes (3): TaskDir(), TestRunReportsInitializedState(), TestRunReportsUninitialized()

### Community 8 - "Community 8"
Cohesion: 0.5
Nodes (2): TestValidateMode(), ValidateMode()

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (2): TestRunInitializesLocalConfigAndState(), StateDirs()

## Knowledge Gaps
- **10 isolated node(s):** `Result`, `Options`, `Task`, `Payload`, `OpenCode` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Run()` connect `Community 5` to `Community 0`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.416) - this node is a cross-community bridge._
- **Why does `runSelfBuild()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`?**
  _High betweenness centrality (0.336) - this node is a cross-community bridge._
- **Why does `LoadLocalConfig()` connect `Community 0` to `Community 1`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.244) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `Run()` (e.g. with `TestRunWarnsWhenOpenCodeMissing()` and `TestRunCapturesOpenCodeVersion()`) actually correct?**
  _`Run()` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Run()` (e.g. with `ConfigFilePath()` and `LoadLocalConfig()`) actually correct?**
  _`Run()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `LoadLocalConfig()` (e.g. with `runSelfBuild()` and `TestSaveAndLoadLocalConfig()`) actually correct?**
  _`LoadLocalConfig()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `ConfigFilePath()` (e.g. with `runSelfBuild()` and `TestConfigFilePath()`) actually correct?**
  _`ConfigFilePath()` has 5 INFERRED edges - model-reasoned connections that need verification._