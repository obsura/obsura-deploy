# Release Workflow

This repository publishes standalone `obsuractl` binaries through GitHub Releases.

## Branch Model

- `dev`
  Integration branch for prerelease validation and preview binaries.
- `main`
  Stable branch for operator-facing releases.

## Pull Requests

Pull requests targeting `dev` or `main` run CI only.

CI performs:

- dependency installation
- unit tests
- Python compile checks
- PyInstaller binary smoke builds for supported platforms

CI does not publish releases and does not create GitHub Releases.

## Dev Branch Releases

Pushes to `dev`:

- run validation
- build standalone `obsuractl` binaries
- generate `checksums.txt`
- publish a GitHub prerelease

Dev tag format:

```text
dev-<shortsha>
```

Example:

```text
dev-a921b32
```

These releases are prereleases and are meant for preview and integration testing.

## Main Branch Releases

Pushes to `main`:

- run validation
- resolve the stable version from the repository source of truth
- build standalone `obsuractl` binaries
- generate `checksums.txt`
- publish a stable GitHub Release
- mark that release as the latest stable release

Stable tag format:

```text
vX.Y.Z
```

Example:

```text
v0.1.0
```

This repository does not create a mutable Git tag named `latest`.

Because every push to `main` attempts a stable release, maintainers must bump the stable CLI version before merging release-worthy changes there. The workflow refuses to reuse an existing stable tag for a different commit.

## Version Source

Stable release version source:

- [cli/obsuractl/version.py](../cli/obsuractl/version.py)

`pyproject.toml` reads the package version dynamically from that module. When maintainers want to publish a new stable release from `main`, they must bump `__version__` there before merging.

## Supported Binary Platforms

Current release matrix:

- `linux-amd64`
- `windows-amd64`

`linux-arm64` and `macos-arm64` are intentionally not shipped in the first release workflow. The current matrix stays limited to the platforms we can validate cleanly in the repository today.

## Binary Branding Assets

Release build artwork lives under [../cli/assets](../cli/assets).

- Windows builds generate a `.ico` file from the committed PNG assets.
- The generated icon is embedded into `obsuractl.exe` during the PyInstaller build.
- Windows builds also embed file version and product metadata so the executable is identifiable in Explorer and release archives.

This keeps binary branding deterministic and tied to the repository, not to ad hoc CI state.

## Asset Naming

Release assets use deterministic names:

```text
obsuractl_<version>_<os>_<arch>.zip
checksums.txt
```

Examples:

- `obsuractl_v0.1.0_linux_amd64.zip`
- `obsuractl_v0.1.0_windows_amd64.zip`
- `obsuractl_dev-a921b32_linux_amd64.zip`

Each archive contains the standalone `obsuractl` executable for that platform.

## Download and Use

Operators can download the appropriate asset from GitHub Releases, extract it, and run:

```bash
./obsuractl --help
```

Windows asset:

```powershell
.\obsuractl.exe --help
```

Verify the archive against `checksums.txt` before distributing it internally.
