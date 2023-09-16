import asyncio

from onepdd.exc import OnePddError


async def exec_cmd_shell(cmd: str) -> str:
    process: asyncio.subprocess.Process = await asyncio.create_subprocess_shell(
        cmd,
        executable="/bin/bash",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            decoded_stderr = ""
            if stderr:
                decoded_stderr = stderr.decode("utf-8")
            raise OnePddError(
                f"Exit code is {process.returncode} for: {cmd!r}. {decoded_stderr}"
            )
    except asyncio.CancelledError:
        process.kill()
        raise
    return stdout.decode() if stdout else ""
