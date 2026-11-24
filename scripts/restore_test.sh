#!/bin/sh
# 백업→복구 시험 (mon에서 root로 실행): 베이스 백업 생성 → 복호화 → WAL 재생 → 주문 수 비교.
# 사용: ssh -p 2222 ubuntu@<mgmt IP> 'sudo sh -s' < scripts/restore_test.sh
set -eu
export PGSSLMODE=require PGPASSFILE=/root/.pgpass
t0=$(date +%s)
/usr/local/bin/gage-basebackup
f=$(ls -t /backup/base/*.enc | head -1)
t1=$(date +%s)
echo "베이스 백업: $(basename "$f") $(du -h "$f" | cut -f1), $((t1 - t0))s (AES-256 암호화)"

r=/restore; rm -rf "$r"; mkdir -p "$r/data"
openssl enc -d -aes-256-cbc -pbkdf2 -pass file:/etc/gage/backup.key -in "$f" | tar -xz -C "$r/data"
wal=$(ls -d /backup/wal/*/ | head -1)
mkdir -p "$r/wal"; cp "$wal"* "$r/wal/"
for p in "$r"/wal/*.partial; do [ -e "$p" ] && cp "$p" "${p%.partial}"; done
touch "$r/data/recovery.signal"
cat >> "$r/data/postgresql.auto.conf" <<EOF
restore_command = 'cp /wal/%f %p'
recovery_target_action = 'promote'
ssl = off
hba_file = '/var/lib/postgresql/data/pg_hba.conf'
EOF
printf 'local all all trust\n' > "$r/data/pg_hba.conf"
rm -f "$r/data/conf.d" 2>/dev/null || true
chown -R 999:999 "$r"; chmod 700 "$r/data"
docker rm -f gage-restore >/dev/null 2>&1 || true
docker run -d --name gage-restore -v "$r/data:/var/lib/postgresql/data" -v "$r/wal:/wal" postgres:16 \
  -c config_file=/var/lib/postgresql/data/postgresql.auto.conf -c hba_file=/var/lib/postgresql/data/pg_hba.conf >/dev/null
for i in $(seq 1 120); do
  docker exec gage-restore psql -U postgres -d gage -Atc "select count(*) from orders" >/tmp/rc 2>/dev/null && break; sleep 1
done
t2=$(date +%s)
echo "복구 완료: $((t2 - t1))s (복호화+WAL 재생+기동)"
echo "복구본 주문 수: $(cat /tmp/rc)"
echo "복구본 마지막 주문 시각: $(docker exec gage-restore psql -U postgres -d gage -Atc 'select max(created_at) from orders')"
echo "전체 RTO(백업 시작→조회 가능): $((t2 - t0))s"
docker rm -f gage-restore >/dev/null; rm -rf "$r"
