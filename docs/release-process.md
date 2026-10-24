# Release process

The project publishes one image per edition: `viewer`, `editor`, and `admin`.

## Version source

`_version.py` is the single version source. Hatch reads it for the package
version. Update `_version.py`, `helm/Chart.yaml`, `README.md`, and
`CHANGELOG.md` in the same pull request.

## Release candidate

1. Create a tag such as `v3.1.0-rc.1` on the release commit.
2. Push the tag. `publish.yml` builds `3.1.0-rc.1-viewer`,
   `3.1.0-rc.1-editor`, and `3.1.0-rc.1-admin`, plus the unsuffixed viewer
   aliases. Prerelease tags do not move the `3.1`, `3`, or `latest` aliases.
3. The GitHub Release is marked as a prerelease.
4. Test the candidate images and the chart.

## Final release

1. Create `v3.1.0` on the merged release commit.
2. Push the tag. The workflow builds the three edition images and creates a
   non-prerelease GitHub Release.
3. Optionally run the `Tag as Stable` workflow with `v3.1.0` to move `stable`
   and `stable-viewer|editor|admin`. It re-tags the published images; it does
   not rebuild them.
4. Publish the Helm chart with the matching `appVersion`.

The `latest` alias moves only for a non-prerelease tag. Prerelease tags keep
their versioned and suffixed tags without moving `latest`, `3`, or `3.1`.

## Required credentials

- `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` for image pushes.
- `GITHUB_TOKEN` with `contents: write` for releases and chart publication.

## GitOps note

Set `requestStateKey.value` or `requestStateKey.existingSecret` and
`requestStateKey.disallowGenerated=true` when rendering the chart with a tool
that cannot use Helm `lookup`. Otherwise each render can generate a new key.
