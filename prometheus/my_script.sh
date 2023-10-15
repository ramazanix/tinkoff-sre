#!/bin/bash

# Генерируем значение метрики
count_of_files_in_directory=$(($(ls -la | wc -l ) - 3))

# Путь к каталогу, где будем хранить метрику
metrics_directory="/var/lib/node_exporter/textfile_collector"

# Имя метрики и файл, в который будем записывать значение
metric_name="count_of_files_in_directory"
metric_file="$metrics_directory/$metric_name.prom"

# Создаем каталог, если его нет
mkdir -p "$metrics_directory"

# Записываем значение метрики в файл формата Prometheus Textfile
echo "# HELP count_of_files_in_directory The count of files in oncall directory
# TYPE count_of_files_in_directory gauge" > "$metric_file"
echo "$metric_name $count_of_files_in_directory" >> "$metric_file"
