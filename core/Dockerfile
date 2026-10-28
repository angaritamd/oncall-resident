# build context: repository root
FROM python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f
WORKDIR /srv
# exact versions with hashes, exported from core/uv.lock (uv export --no-dev --format requirements-txt)
COPY core/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
COPY adapters /srv/adapters
COPY core/oncall_core /srv/oncall_core
COPY demo/seed/cases.json /srv/cases.json
COPY demo/seed/reports.json /srv/reports.json
COPY demo/seed/review_cases.json /srv/review_cases.json
COPY demo/seed/review_reports.json /srv/review_reports.json
ENV CASES_FILE=/srv/cases.json REPORTS_SEED=/srv/reports.json PYTHONPATH=/srv STATE_DB=/data/oncall.db
ENV REVIEW_REPORTS_SEED=/srv/review_reports.json
# persistent state (activity log, arrival times); a fresh named volume inherits this ownership
RUN mkdir -p /data && chown nobody:nogroup /data
USER nobody
EXPOSE 8000
CMD ["uvicorn", "oncall_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
