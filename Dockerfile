FROM futureys/claude-code-python-development:20260221145500
COPY pyproject.toml /workspace/
# - Using uv in Docker | uv
#   https://docs.astral.sh/uv/guides/integration/docker/#caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python 3.13
COPY . /workspace
ENTRYPOINT [ "uv", "run" ]
CMD ["invoke", "test.coverage"]
