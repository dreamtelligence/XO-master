# Repository setup

The default branch builds and tests the Artist Workspace with GitHub Actions. These checks use synthetic audio and need no cloud credentials.

See [local setup](../README.md) to run the app and [private Modal setup](../docs/PRIVATE_MODE.md) to connect the model workers. Each operator creates private credentials in their own Modal workspace.

See [hosting and deployment](../docs/verification/2026-11-18-artist-workspace-online.md) to run a protected studio. The production deployment is separate from pushes to GitHub.
