<!-- This file is templated with https://pkg.go.dev/html/template -->
👋  Hey! Here is the image we built for you ([Artifactory Link](https://artifactory.algol60.net/ui/repos/tree/General/csm-docker%2F{{ .stableString }}%2F{{ .imageName }}%2F{{ .imageTag }})):

```bash
{{ .image }}
```

Use podman or docker to pull it down and inspect locally:

```bash
podman pull {{ .image }}
```

Or, use this script to pull the image from the build server to a dev system:

<details>
<summary>Dev System Pull Script</summary>
<br />

> **Note** the following script only applies to systems running CSM 1.2 or later.

```bash
#!/usr/bin/env bash
export REMOTE_IMAGE={{ .image }}
export LOCAL_IMAGE={{ .imageName }}:{{ .imageTag }}

skopeo copy --dest-tls-verify=false docker://${REMOTE_IMAGE} docker://registry.local/csm-docker/stable/${LOCAL_IMAGE}
```
</details>

<details>
<summary>Software Bill of Materials</summary>
<br />

```bash
cosign download sbom {{ .image }} > container_image.spdx
```

If you don't have cosign, then you can get it [here](https://github.com/sigstore/cosign#installation).
</details>

*Note*: this SHA is the merge of {{ .PRHeadSha }} and the PR base branch. Good luck and make rocket go now! 🌮 🚀