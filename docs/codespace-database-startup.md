# Codespace PostgreSQL Başlatma Notu

Bu proje Codespaces ortamında lokal PostgreSQL container'ı kullanır.

## Her Codespace açılışında

Repo köküne geç:

```bash
cd /workspaces/stock-fund-predictor
```

Mevcut PostgreSQL container'ını başlat:

```bash
docker start stock-fund-predictor-postgres
```

Kontrol et:

```bash
docker ps --filter "name=stock-fund-predictor-postgres"
```

Beklenen durum:

```text
STATUS: Up
PORTS: 0.0.0.0:5432->5432/tcp
```

Ardından backend komutları çalıştırılabilir:

```bash
cd /workspaces/stock-fund-predictor/backend
```

## Önemli: `docker compose up -d postgres` neden conflict verebilir?

`compose.yml` içinde sabit container adı kullanılıyor:

```yaml
container_name: stock-fund-predictor-postgres
```

Bu nedenle container zaten mevcut fakat durmuş durumdaysa:

```bash
docker compose up -d postgres
```

komutu yeni container oluşturmaya çalışırken:

```text
Conflict. The container name "/stock-fund-predictor-postgres" is already in use
```

hatası verebilir.

Bu durumda **container'ı silme**. Önce:

```bash
docker ps -a --filter "name=stock-fund-predictor-postgres"
docker start stock-fund-predictor-postgres
```

kullan.

## Container çalışmıyorsa

Container'ın durumunu kontrol et:

```bash
docker ps -a --filter "name=stock-fund-predictor-postgres"
```

`Exited` durumundaysa:

```bash
docker start stock-fund-predictor-postgres
```

başlat.

Başlatma başarısız olursa logları kontrol et:

```bash
docker logs --tail 100 stock-fund-predictor-postgres
```

PostgreSQL loglarında şu mesaj görülüyorsa database bağlantı kabul etmeye hazırdır:

```text
database system is ready to accept connections
```

## Veri kaybına karşı önemli not

PostgreSQL verisi Docker named volume üzerinde tutuluyor:

```text
postgres_data
```

Bu nedenle mevcut container/volume'u gereksiz yere silme. Özellikle:

```bash
docker rm stock-fund-predictor-postgres
docker compose down -v
```

komutlarını veri kaybı ihtimalini değerlendirmeden kullanma.

## Migration

PostgreSQL çalıştıktan sonra gerekirse:

```bash
cd /workspaces/stock-fund-predictor/backend
PYTHONPATH=. alembic upgrade head
```

çalıştırılabilir.

## Gerçek backtest öncesi

Database bağlantısı çalışmadan gerçek-data backtest smoke testi çalışmaz. Örneğin:

```bash
PYTHONPATH=. python scripts/smoke_test_backtest_real.py \
  --symbol THYAO \
  --days 1000 \
  --gap 5
```

öncesinde PostgreSQL container'ının `Up` durumda olduğundan emin ol.

## Yeni sohbette devam kuralı

Projeye yeni bir sohbette devam ederken bu dosya ve `docs/progress.md` okunmalıdır. Codespace yeniden açıldıysa ilk kontrol PostgreSQL container'ının durumudur.
