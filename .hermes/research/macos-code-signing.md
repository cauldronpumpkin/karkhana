# Tauri v2 macOS Code Signing

> Source: Gemini Deep Research
> Email subject: Re: [Karkhana Deep Research] Tauri v2 macOS Code Signing
> Thread: 19dfcd38b7946011

Comprehensive Technical Report on macOS Code Signing and Notarization for
Tauri v2 Applications
The transition of the macOS software ecosystem toward a zero-trust
architecture has necessitated a rigorous multi-stage verification pipeline
for third-party developers. For those utilizing Tauri v2—a framework that
combines the performance of Rust with modern web frontends—this pipeline is
not an optional enhancement but a functional requirement for distribution.
Without a valid code signature and a corresponding notarization ticket from
Apple’s security servers, applications downloaded via the internet are
subjected to Gatekeeper interventions that effectively block the execution
of the software, presenting users with messages stating the application is
"broken" or "from an unidentified developer". This report provides an
exhaustive analysis of the infrastructure, cryptographic requirements, and
automated workflows necessary to move a Tauri v2 application from source
code to a fully notarized and distributable Disk Image (.dmg). [1][2]
The Economics and Infrastructure of the Apple Developer Program
The primary prerequisite for distributing macOS software is enrollment in
the Apple Developer Program. This program serves as the root of trust for
all issued identities, linking a developer's cryptographic keys to a
verified real-world identity.
Enrollment Tiers and Financial Commitments
Apple maintains a standardized pricing structure for its developer
programs, which remains consistent globally, adjusted for local currencies.
For individual developers and organizations, the cost is significantly
higher than alternative platforms like the Google Play Store, which
requires a one-time fee.
Program Tier
Annual Cost (USD)
Verification Requirements
Primary Distribution Target
Individual
$99
Personal ID, 2FA, Apple Developer App verification
App Store and Direct (Developer ID)
Organization
$99
D-U-N-S Number, Legal Entity status, Binding authority
App Store and Direct (Developer ID)
Enterprise
$299
Verification of 100+ employees, D-U-N-S Number
Internal In-House Distribution only

The annual $99 fee is a recurring requirement. Failure to renew the
membership prevents the developer from signing new updates, although
existing applications signed while the certificate was valid will generally
continue to run unless they utilize advanced features like provisioning
profiles. While individual enrollment is often processed within 24 to 48
hours, organizational enrollment frequently encounters significant
delays. [1]
Organizational Verification and the D-U-N-S Protocol
Organizations must navigate a more complex verification landscape. The
cornerstone of this process is the Data Universal Numbering System
(D-U-N-S) number, a unique nine-digit identifier provided by Dun &
Bradstreet. This identifier is used by Apple to confirm the legal existence
and active status of the business entity. The process of obtaining a
D-U-N-S number can take several business days, and the subsequent
synchronization between Dun & Bradstreet's database and Apple’s systems can
add further delays to the timeline. [1]
The verification of "Legal Binding Authority" is another critical step. The
person enrolling the organization must prove they are authorized to enter
into legal contracts on behalf of the company. In 2026, developers have
noted that the timeline for organizational approval typically ranges from
two to three weeks, though proactive communication with Apple Support can
sometimes resolve "stuck" applications in a matter of minutes. [1]
Cryptographic Identity and Certificate Architecture
The security of the macOS distribution model is built upon Public Key
Infrastructure (PKI). A "Signing Identity" is the combination of a digital
certificate (the public key) issued by Apple and a private key stored
securely on the developer's hardware.
Distinguishing Between Developer ID Certificate Types
For Tauri applications distributed outside the Mac App Store—the most
common path for Tauri developers—the "Developer ID" certificate family is
used. There are two specific types that serve distinct roles in the
distribution process.
Certificate Name
Purpose
Target Artifacts
Developer ID Application
Signs the executable and the application bundle
.app bundles, Mach-O binaries,.dmg files
Developer ID Installer
Signs the flat installer package
.pkg installer files

For a standard Tauri build that produces a.dmg, the Developer ID
Application certificate is the essential requirement. It ensures that the
application has not been tampered with since it was signed and identifies
the developer to Gatekeeper. Apple imposes a strict limit of five active
certificates of each type per developer account, necessitating careful
management and revocation of old or compromised keys. [1][2][3][4]
The Certificate Signing Request (CSR) Workflow
Generating a signing identity requires a secure handshake between the
developer's Mac and Apple’s certificate authority.
The resulting identity string, such as Developer ID Application: Your Name
(TEAMID), is the unique identifier that the Tauri bundler uses to locate
the correct key in the system keychain for the signing process.
The Hardened Runtime and Entitlement Manifests
Notarization introduces a requirement beyond simple code signing: the
Hardened Runtime. Introduced in macOS 10.14, the Hardened Runtime is a
security feature that protects applications from runtime attacks by
restricting certain capabilities of the process. [1][2][3]
Security Constraints of the Hardened Runtime
When an application is signed with the "runtime" option enabled, the macOS
kernel enforces a set of restrictions designed to prevent code injection
and memory tampering.
Entitlements for Tauri Applications
Because Tauri applications rely on the WRY library and the WebKit engine,
they often require exceptions to these strict rules. These exceptions are
declared in an "Entitlements" property list file (.plist) included in the
signing command.
Entitlement Key
Tauri Use Case
com.apple.security.cs.allow-jit
Required for the JavaScript engine's Just-In-Time compilation in the WebView
com.apple.security.cs.allow-unsigned-executable-memory
Often needed for plugins or external libraries that generate code at runtime
com.apple.security.network.client
Essential for any application that needs to make outgoing HTTP requests
com.apple.security.cs.disable-library-validation
Required if the app needs to load third-party plugins not signed by the
developer

For Tauri v2, developers typically create a file named entitlements.plist
in the src-tauri directory and reference it in the tauri.conf.json bundle
configuration. Failure to include the allow-jit entitlement is a frequent
cause of "white screen" errors in production builds, as the WebView process
is killed by the kernel for violating memory protections. [1][2]
The Notarization Workflow: Implementation via Notarytool
Notarization is an automated audit process where Apple's servers scan the
signed software for known malware and security issues. Since November 2023,
the legacy altool has been fully decommissioned in favor of notarytool,
which provides a faster and more modern interface. [1][2]
Authentication and Credentials
Interacting with the Apple Notary Service requires authenticated access.
Developers have two primary methods for providing credentials to the tauri
build process.
Submission, Validation, and Stapling
The notarization pipeline follows a strict sequence after the Tauri bundler
has finished compiling and signing the application.
Tauri v2 Configuration Mechanics
Tauri v2 abstracts the complexity of codesign and notarytool through its
native bundler. This integration is managed primarily through the
tauri.conf.json file.
Bundle Configuration in tauri.conf.json
The bundle object must be correctly populated to trigger the automated
signing and notarization steps.
The signingIdentity can be the full name of the certificate or just the
Team ID in parentheses. If this field is left as null, the bundler will
attempt to search the local keychain for a valid Developer ID Application
certificate. [1][2][3]
Environment Variables for Automation
During the build process, Tauri looks for specific environment variables to
authenticate the notarization request.
Environment Variable
Description
Source
APPLE_ID
Apple ID email address
appleid.apple.com
APPLE_PASSWORD
App-specific password
appleid.apple.com
APPLE_TEAM_ID
10-character Team ID
Developer Account Details
APPLE_API_ISSUER
UUID for the API key issuer
App Store Connect Integrations
APPLE_API_KEY
Key ID for the API key
App Store Connect Integrations

By setting these variables in the local environment or a CI/CD pipeline,
the tauri build command will automatically handle the upload, wait for
approval, and attempt to staple the result. [1][2][3][4][5]
CI/CD Integration: GitHub Actions Workflow
Building and signing macOS applications on GitHub Actions is a complex task
because the runner's environment is ephemeral and does not contain the
developer's private keys.
Exporting and Encoding the Digital Identity
To use a certificate in a CI environment, it must be exported from the
local Mac as a PKCS #12 (.p12) file. This file is then converted to a
base64 string to be stored as a GitHub Secret.
The Runner Keychain Preparation
The GitHub Actions workflow must recreate a keychain and import the
certificate before the Tauri build begins. A critical step in this process
is the "partition list" configuration, which prevents the build from
hanging on a GUI password prompt.
The set-key-partition-list command is the most vital for automation. It
grants the codesign tool permission to access the imported key without
requiring manual user interaction. [1]
Troubleshooting and Maintenance of the Signing Pipeline
Even with a mature pipeline, developers often encounter errors related to
the deep nesting of modern applications.
Deep Signing and Nested Binaries
A common failure in notarization is the "invalid signature" error. This
usually occurs because a binary or library nested inside the .app bundle
was not signed, or its signature was invalidated by a subsequent
modification. Tauri's bundler attempts to sign recursively, but developers
using "sidecars" (external binaries) must ensure these sidecars are signed
with the same identity. [1]
Secure Timestamps and SDK Requirements
Apple's Notary Service requires that all signatures include a "secure
timestamp." This timestamp proves that the code was signed while the
developer's certificate was still valid. By default, Tauri's bundler
includes this, but developers using custom build scripts must include the
--timestamp flag in their codesign invocations. Furthermore, applications
must be linked against the macOS 10.9 SDK or newer, as older signing
formats are no longer supported by the notary service. [1]
Alternative Tools and Third-Party Services
For teams that find the native Apple toolchain restrictive—particularly
those wanting to sign macOS apps from Linux or Windows—several alternatives
have emerged.
Open Source Implementations: rcodesign
The apple-codesign project is a pure Rust implementation of Apple's signing
and notarization logic. It allows for the signing of Mach-O binaries and
the submission of notarization requests from non-Apple platforms.
Managed Services: CrabNebula Cloud
CrabNebula, a primary contributor to the Tauri ecosystem, provides
"Taurify," a cloud-based distribution service. Taurify can manage the
signing and notarization process, even offering a "CrabNebula-signed"
wrapper for developers who are still waiting for their Apple Developer
Program approval. This service significantly lowers the barrier to entry
for early-stage projects that need to distribute test versions of their
software without Gatekeeper warnings. [1][2]
Timeline and Lifecycle Estimates for First-Time Setup
For a new developer or organization, the transition from zero to a
notarized.dmg involves several dependencies with varying lead times.
Stage
Estimated Duration
Dependencies
D-U-N-S Registration
1–5 Business Days
Business documentation
Apple Developer Approval
1–14 Days
Identity verification, D-U-N-S sync
Certificate/ID Setup
1 Hour
Mac hardware, Keychain Access
Tauri Configuration
1–2 Hours
Entitlements, tauri.conf.json
CI/CD Setup
3–6 Hours
Secret management, workflow debugging
First Notarization Run
5–60 Minutes
Apple Notary Service status

The total "wall-clock" time for an organization is often two to three
weeks, primarily due to the administrative overhead of identity
verification. For an individual developer with an existing Apple Account,
the entire process can often be completed in under 48 hours. [1][2]
Conclusion: Strategic Implementation for Tauri v2
The macOS code signing and notarization pipeline is a sophisticated
deterrent against malware that requires developers to adopt a
"security-first" build mentality. For Tauri v2 developers, success lies in
the meticulous management of cryptographic identities and the correct
declaration of entitlements. By leveraging the native integration within
the Tauri bundler and augmenting it with robust CI/CD practices using
GitHub Actions, developers can create a seamless deployment pipeline. [1][2]
While third-party tools like rcodesign provide powerful alternatives for
cross-platform workflows, the native notarytool remains the most reliable
path for most projects. As macOS continues to evolve—moving toward even
stricter runtime protections in versions like macOS Sequoia—maintaining a
clean, automated signing pipeline is not just a technical task, but a vital
component of professional software maintenance and user safety. Developers
should treat their .p12 certificates and API keys as high-value assets,
ensuring they are stored securely and rotated regularly to maintain the
integrity of their distributed software.

1. https://v2.tauri.app/distribute/sign/macos/ (macOS Code Signing - Tauri)
2.
https://dev.to/tomtomdu73/ship-your-tauri-v2-app-like-a-pro-code-signing-for-macos-and-windows-part-12-3o9n
(Ship Your Tauri v2 App Like a Pro: Code Signing for macOS and Windows
(Part 1/2))
3. https://developer.apple.com/help/account/membership/program-enrollment/
(Enrollment - Membership - Account - Help - Apple Developer)
4.
https://www.reddit.com/r/appledevelopers/comments/1scsvh7/how_long_did_apple_developer_program_approval/
(How long did Apple Developer Program approval take for your corporation?
(Canadian corp, D-U-N-S verified) : r/appledevelopers - Reddit)
5. https://www.freecodecamp.org/news/apple-code-signing-handbook/ (The
Apple Code Signing Handbook - freeCodeCamp)


On Wed, May 6, 2026 at 3:56 PM <cauldronpumpkin@gmail.com> wrote:

> Research task: Tauri v2 macOS code signing — full process from Apple
> Developer account to notarized .dmg.
>
> Please cover:
> - Apple Developer account requirements and costs (9/yr individual, 99/yr
> org?)
> - Certificate types needed (Developer ID Application, Developer ID
> Installer)
> - Notarization workflow (xcrun notarytool submit, staple)
> - Entitlements and hardened runtime requirements
> - CI/CD integration (GitHub Actions secrets for certificates)
> - Timeline estimate for first-time setup
> - Any third-party services that simplify this (e.g., notarytool
> alternatives)
>
> Reply to this thread with your Gemini Deep Research results (paste as text
> or attach .md/.txt).
