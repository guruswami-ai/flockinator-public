# Reproduce the flagship communication benchmark. Stdlib-only scientific code;
# no dependencies to install, no network or credentials at runtime.
FROM python:3.12-slim@sha256:31ba4539f4c926d93ebcc0d31a68f94797c5d76ede54698b75d5c1d87a12f2e7
WORKDIR /app
COPY tools/mission-host/coordination_lab.py tools/mission-host/planner.py tools/mission-host/exercise_memory.py /app/mission-host-src/
COPY tools/reproduce/run.py tools/reproduce/expected.json /app/reproduce/
# run.py resolves the repo root as ../../../ from its location; in the image we
# place sources to match that layout.
RUN mkdir -p /app/tools/mission-host /app/tools/reproduce \
 && cp /app/mission-host-src/*.py /app/tools/mission-host/ \
 && cp /app/reproduce/run.py /app/reproduce/expected.json /app/tools/reproduce/ \
 && rm -rf /app/mission-host-src /app/reproduce \
 && useradd -m repro && chown -R repro /app
USER repro
ENTRYPOINT ["python3", "/app/tools/reproduce/run.py"]
CMD ["--out", "/tmp/out"]
