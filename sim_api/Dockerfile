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

RUN chmod +x simulate.jl

EXPOSE 5000

# set up flask via env variables
ENV FLASK_APP=api.py \
    FLASK_RUN_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

# entry point is the flask dev server
CMD ["flask", "run", "--port", "5000"]
