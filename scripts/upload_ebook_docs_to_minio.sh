#!/usr/bin/env bash
set -euo pipefail

MINIO_ALIAS="${MINIO_ALIAS:-zuoti-local}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-https://www.njwjxy.cn:30443}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-}"
DOC_DIR="${1:-/root/zuoti/doc}"
TARGET_PREFIX="zuoti-minio/public-assets/docs/ebooks"

if [[ -z "$MINIO_ACCESS_KEY" || -z "$MINIO_SECRET_KEY" ]]; then
  echo "MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required" >&2
  exit 1
fi

mc alias set "$MINIO_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null

declare -A FILE_MAP=(
  ["1_医药商品购销员-基础知识.pdf"]="ebook-01-basic-knowledge.pdf"
  ["1_医药商品购销员-初级.pdf"]="ebook-02-primary.pdf"
  ["1_医药商品购销员职业资格知识与技能综合训练-习题集.pdf"]="ebook-03-workbook.pdf"
  ["医药商品购销员（中级）.pdf"]="ebook-04-intermediate.pdf"
  ["医药商品购销员（指南包 课程包）.pdf"]="ebook-05-guide-course-pack.pdf"
  ["医药商品购销员（高级）.pdf"]="ebook-06-advanced.pdf"
  ["药品购销技术.pdf"]="ebook-07-pharma-sales-technique.pdf"
)

for source_name in "${!FILE_MAP[@]}"; do
  source_path="$DOC_DIR/$source_name"
  target_name="${FILE_MAP[$source_name]}"
  if [[ ! -f "$source_path" ]]; then
    echo "missing file: $source_path" >&2
    exit 1
  fi
  mc cp "$source_path" "$MINIO_ALIAS/$TARGET_PREFIX/$target_name" >/dev/null
done

echo "Uploaded ${#FILE_MAP[@]} ebook documents to $MINIO_ALIAS/$TARGET_PREFIX"
