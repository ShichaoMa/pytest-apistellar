import asyncio


def get_coroutine(ret_val):
    async def inner():
        if asyncio.iscoroutine(ret_val):
            await ret_val
        return ret_val
    return inner()

