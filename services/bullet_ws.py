"""
轻量 WebSocket 广播服务（用于实时推送弹幕到前端）。
如果环境中没有安装 `websockets` 包，模块会静默失败并回退到轮询机制。

启动：在 app 启动后调用 start_server(host, port)
广播：调用 broadcast({'type':'bullet', ...})
"""
import threading
import json
import logging

logger = logging.getLogger(__name__)

_websockets = None
_loop = None
_server = None
_clients = set()

try:
    import asyncio
    import websockets
    _websockets = websockets
except Exception:
    _websockets = None


async def _handler(ws, path):
    # 注册客户端
    _clients.add(ws)
    logger.info(f"WS 客户端已连接: {ws.remote_address}")
    try:
        async for _ in ws:
            # 本服务为单向广播，忽略客户端消息
            continue
    except Exception:
        pass
    finally:
        try:
            _clients.discard(ws)
        except Exception:
            pass
        logger.info(f"WS 客户端断开: {ws.remote_address}")


async def _broadcast_json(obj):
    if not _clients:
        return
    data = json.dumps(obj, ensure_ascii=False)
    coros = []
    for ws in list(_clients):
        try:
            coros.append(ws.send(data))
        except Exception:
            try:
                _clients.discard(ws)
            except Exception:
                pass
    if coros:
        await asyncio.wait(coros)


def start_server(host='127.0.0.1', port=6789):
    """在后台线程启动 WebSocket 服务器；返回 True 表示已启动，False 表示不可用（缺少依赖）"""
    global _loop, _server
    if _websockets is None:
        logger.warning('websockets 库不可用，WebSocket 广播未启用')
        return False

    def _run():
        global _loop, _server
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        start_coro = _websockets.serve(_handler, host, port)
        _server = _loop.run_until_complete(start_coro)
        logger.info(f'WebSocket 广播服务已启动 -> ws://{host}:{port}')
        try:
            _loop.run_forever()
        finally:
            try:
                _server.close()
                _loop.run_until_complete(_server.wait_closed())
            except Exception:
                pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return True


def broadcast(obj):
    """向所有已连接客户端广播 JSON 可序列化对象。"""
    global _loop
    if _websockets is None or _loop is None:
        return False
    try:
        fut = asyncio.run_coroutine_threadsafe(_broadcast_json(obj), _loop)
        # 不阻塞，丢弃结果
        return True
    except Exception as e:
        logger.warning(f'广播失败: {e}')
        return False
