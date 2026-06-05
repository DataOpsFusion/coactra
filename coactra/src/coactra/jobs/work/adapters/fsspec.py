"""Artifact persistence through fsspec-compatible filesystems."""

from __future__ import annotations

from urllib.parse import quote

from coactra.jobs.work.adapters._optional import optional_module
from coactra.jobs.work.domain.artifacts import Artifact, ArtifactRef
from coactra.jobs.work.domain.scope import Scope

_MEDIA_TYPE = "application/vnd.coactra.artifact+json"


class FsspecArtifactStore:
    """Store artifact envelopes on local, S3, GCS, and other fsspec filesystems."""

    def __init__(self, base_uri: str, *, fs=None) -> None:
        self.base_uri = base_uri.rstrip("/")
        if fs is None:
            fsspec = optional_module("fsspec.core", extra="fsspec")
            fs, root = fsspec.url_to_fs(self.base_uri)
        else:
            root = self.base_uri
        self.fs = fs
        self.root = root.rstrip("/")

    def put(self, artifact: Artifact, scope: Scope) -> ArtifactRef:
        relative = self._relative(scope, artifact.id)
        path = self._path(relative)
        parent = path.rsplit("/", 1)[0]
        self.fs.makedirs(parent, exist_ok=True)
        with self.fs.open(path, "w") as file:
            file.write(artifact.model_dump_json())
        return ArtifactRef(
            uri=f"{self.base_uri}/{relative}",
            media_type=_MEDIA_TYPE,
            name=artifact.name,
        )

    def get(self, reference: ArtifactRef, scope: Scope) -> Artifact:
        relative = self._relative_from_reference(reference, scope)
        with self.fs.open(self._path(relative), "r") as file:
            return Artifact.model_validate_json(file.read())

    def _relative_from_reference(self, reference: ArtifactRef, scope: Scope) -> str:
        base_prefix = f"{self.base_uri}/"
        scope_prefix = f"{self._scope_prefix(scope)}/"
        if not reference.uri.startswith(base_prefix):
            raise ValueError("artifact reference is outside the requested scope")
        relative = reference.uri.removeprefix(base_prefix)
        if not relative.startswith(scope_prefix):
            raise ValueError("artifact reference is outside the requested scope")
        filename = relative.removeprefix(scope_prefix)
        if not filename or "/" in filename or not filename.endswith(".json"):
            raise ValueError("artifact reference is not a scoped artifact envelope")
        return relative

    def _relative(self, scope: Scope, artifact_id: str) -> str:
        return f"{self._scope_prefix(scope)}/{quote(artifact_id, safe='')}.json"

    def _scope_prefix(self, scope: Scope) -> str:
        return f"{quote(scope.tenant_id, safe='')}/{quote(scope.namespace, safe='')}/artifacts"

    def _path(self, relative: str) -> str:
        return f"{self.root}/{relative}" if self.root else relative
