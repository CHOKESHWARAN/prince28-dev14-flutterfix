from flutterfix.config import Settings


def test_git_sha_uses_render_commit_when_image_sha_is_default(monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "render-commit")

    assert Settings(app_env="ci").git_sha == "render-commit"


def test_git_sha_prefers_embedded_image_sha(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "image-commit")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "render-commit")

    assert Settings(app_env="ci").git_sha == "image-commit"
