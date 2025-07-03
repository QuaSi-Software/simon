# syntax=docker/dockerfile:1

FROM julia:1.11.5-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# pip / PEP 668 Workaround (Debian Bookworm & Ubuntu 24.04)
# ---------------------------------------------------------------------------
# Debian now marks its Python installation as “externally managed” (PEP 668),
# causing `pip install` to fail unless you opt‑in. In containers we usually *do*
# want to install into the system site‑packages, so we set the env var below.
# (Alternative: create a virtualenv instead.)
ENV PIP_BREAK_SYSTEM_PACKAGES=1

WORKDIR /app

# copying the requirements file alone before the rest of the code somehow leverages
# layer caching for better performance?
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ./

# install the package for itself
RUN pip3 install -e .

EXPOSE 5000
# set up flask via env variables
ENV FLASK_APP=/app/sim_api/api.py \
    FLASK_RUN_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

# other env variables
ENV SIM_NR_THREADS=1

RUN chmod +x start.sh
# entry point is a script that runs the flask server and starts the scanner
CMD ["./start.sh"]
