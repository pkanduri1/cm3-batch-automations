FROM registry.access.redhat.com/ubi8/python-39

# Switch to root for system installations
USER root

# Set working directory
WORKDIR /app

# Install system dependencies for Oracle Instant Client
RUN yum install -y \
    wget \
    unzip \
    libaio \
    && yum clean all

# Install Oracle Instant Client 19c for RHEL 8
RUN wget https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && unzip instantclient-basic-linux.x64-19.23.0.0.0dbru.zip -d /opt/oracle \
    && rm instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && echo /opt/oracle/instantclient_19_23 > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

# Set Oracle environment variables
ENV ORACLE_HOME=/opt/oracle/instantclient_19_23
ENV LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
ENV PATH=$ORACLE_HOME:$PATH

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/samples data/mappings reports && \
    chmod -R 775 logs data reports

# Set Python path
ENV PYTHONPATH=/app

# Switch back to non-root user for security
USER 1001

# Default command
CMD ["python", "-m", "pytest"]
