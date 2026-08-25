FROM apache/spark:3.5.1

USER root
RUN pip install psycopg2-binary

COPY app /app

USER spark

CMD sh -c "/opt/spark/bin/spark-submit --master ${SPARK_MASTER_URL} --conf spark.jars.ivy=/tmp/.ivy2 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.7.3 /app/main.py"
