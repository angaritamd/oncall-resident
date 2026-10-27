# build context: repository root
FROM python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f
WORKDIR /srv
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.30" "httpx>=0.27"
COPY adapters /srv/adapters
COPY core/oncall_core /srv/oncall_core
COPY demo/seed/cases.json /srv/cases.json
ENV CASES_FILE=/srv/cases.json PYTHONPATH=/srv
USER nobody
EXPOSE 8000
CMD ["uvicorn", "oncall_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
