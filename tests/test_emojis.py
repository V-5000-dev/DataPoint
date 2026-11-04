import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cogs import delete_table, dev_control, table_settings
from config import DANDER, ERROR, PERMISSON, X
from conftest import make_member, make_table


def interaction(user=None):
    return SimpleNamespace(
        user=user or make_member(),
        guild=SimpleNamespace(id=1),
        response=SimpleNamespace(send_message=AsyncMock(), edit_message=AsyncMock()),
    )


def sent_text(fake):
    return fake.response.send_message.await_args.args[0]


def test_ordinary_column_errors_use_the_error_emoji():
    async def run():
        add = table_settings.AddColumn_Input(make_table())
        add.column_name._value = "Age"
        fake = interaction()
        await add.on_submit(fake)
        assert sent_text(fake).startswith(ERROR)

        remove = table_settings.RemoveColumn_Input(make_table())
        remove.column_name._value = "Missing"
        fake = interaction()
        await remove.on_submit(fake)
        assert sent_text(fake).startswith(ERROR)

    asyncio.run(run())


@pytest.mark.parametrize("button", ["confirm", "cancel"])
def test_someone_elses_delete_prompt_uses_the_permission_emoji(button):
    async def run():
        view = delete_table.DeleteTableConfirm(make_table(), make_member(1), 1)
        fake = interaction(make_member(2))
        await getattr(view, button).callback(fake)
        assert sent_text(fake).startswith(PERMISSON)

    asyncio.run(run())


def test_cancelling_a_delete_uses_the_no_emoji():
    async def run():
        requester = make_member(1)
        view = delete_table.DeleteTableConfirm(make_table(), requester, 1)
        fake = interaction(requester)
        await view.cancel.callback(fake)
        assert fake.response.edit_message.await_args.kwargs["content"].startswith(X)

    asyncio.run(run())


def test_delete_prompt_is_a_warning_not_an_error():
    async def run():
        ctx = SimpleNamespace(
            author=make_member(administrator=True),
            bot=SimpleNamespace(get_channel=lambda channel_id: None),
            guild=SimpleNamespace(id=1),
            command=SimpleNamespace(name="delete-table"),
            send=AsyncMock(),
        )
        import config
        config.get_guild(1)["ALL_TABLES"].append(make_table("A"))
        cog = delete_table.Delete_Table(None)
        await cog.table_delete_prefix.callback(cog, ctx, "A")
        assert ctx.send.await_args.args[0].startswith(DANDER)

    asyncio.run(run())


def owner_ctx():
    return SimpleNamespace(send=AsyncMock())


@pytest.mark.parametrize("path,emoji", [
    (".env", PERMISSON),
    ("/etc/hosts", PERMISSON),
    ("missing.txt", ERROR),
])
def test_cat_failures_use_the_right_emoji(path, emoji):
    async def run():
        cog = dev_control.Dev_Control(None)
        ctx = owner_ctx()
        await cog.dev_cat.callback(cog, ctx, path)
        assert ctx.send.await_args.args[0].startswith(emoji)

    asyncio.run(run())
