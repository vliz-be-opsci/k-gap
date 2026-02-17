FROM python:3.10-slim

# Copy wrapper scripts
COPY ./kgap /kgap
RUN chmod +x /kgap/*.sh /kgap/*.py

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r /kgap/requirements.txt

# Set the entrypoint
ENTRYPOINT ["/kgap/entrypoint.sh"]
