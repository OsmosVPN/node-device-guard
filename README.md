# node-device-guard

Агент, устанавливаемый на каждую VPN-ноду. Получает список IP-адресов от panel-device-guard и мгновенно сбрасывает их активные соединения через `conntrack`.

## Зачем

Когда panel-device-guard банит пользователя (ставит `status=disabled` в Marzban), уже установленные TCP-соединения продолжают работать. node-device-guard решает это: принудительно дропает соединения через `conntrack -D -s <ip>` в момент бана.

## Как работает

```
panel-device-guard (бан)
    └─ POST /kick {"ips": ["1.2.3.4", ...]}
           └─ node-device-guard
                  └─ conntrack -D -s 1.2.3.4   (сброс соединения)
```

## API

### `GET /health`

Healthcheck. Возвращает `{"ok": true}`.

### `POST /kick`

Сбрасывает соединения для указанных IP.

**Заголовки:**

```
Authorization: Bearer <NODE_KICK_TOKEN>
Content-Type: application/json
```

**Тело:**

```json
{ "ips": ["1.2.3.4", "5.6.7.8"] }
```

**Ответ:**

```json
{
  "results": {
    "1.2.3.4": "ok",
    "5.6.7.8": "not_found"
  }
}
```

Возможные статусы для каждого IP:

| Статус              | Описание                                |
| ------------------- | --------------------------------------- |
| `ok`                | Соединение успешно сброшено             |
| `not_found`         | Активных записей в conntrack не найдено |
| `invalid`           | Невалидный IP-адрес                     |
| `timeout`           | conntrack завис (>5 сек)                |
| `conntrack_missing` | `conntrack-tools` не установлен на ноде |
| `error`             | Прочая ошибка                           |

## Переменные окружения

| Переменная        | По умолчанию | Описание                                                                                 |
| ----------------- | ------------ | ---------------------------------------------------------------------------------------- |
| `NODE_KICK_PORT`  | `62010`      | Порт HTTP-сервера                                                                        |
| `NODE_KICK_TOKEN` | —            | Shared secret (Bearer token). Если не задан — эндпоинт `/kick` открыт без аутентификации |

## Деплой через Docker (рекомендуется)

```bash
cp .env.example .env
# Заполни NODE_KICK_TOKEN — тот же что в panel-device-guard .env
docker compose up -d
```

> `network_mode: host` и `cap_add: NET_ADMIN` обязательны — иначе conntrack не увидит соединения хоста.

## Деплой без Docker

```bash
apt install -y conntrack python3 python3-pip
pip3 install aiohttp

NODE_KICK_PORT=62010 NODE_KICK_TOKEN=your-secret python3 agent.py
```

Для автозапуска через systemd:

```ini
# /etc/systemd/system/node-device-guard.service
[Unit]
Description=node-device-guard
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/node-device-guard/agent.py
Restart=always
Environment=NODE_KICK_PORT=62010
Environment=NODE_KICK_TOKEN=your-secret

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now node-device-guard
```

## Требования на ноде

- Linux с `conntrack-tools` (`apt install conntrack-tools`)
- Python 3.10+ или Docker
- Порт `NODE_KICK_PORT` доступен только с сервера panel-device-guard (лучше закрыть файрволом для всех остальных)

## Безопасность

- Всегда задавай `NODE_KICK_TOKEN` — случайную строку не менее 32 символов
- Закрой порт файрволом: разрешай только IP-адрес сервера с panel-device-guard
- Агент не принимает shell-команды — IP валидируется через `ipaddress.ip_address()` перед передачей в conntrack
