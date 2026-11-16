"""Gradio app for the Sidekick. Run with: uv run app.py"""

import asyncio
import html
import os

import gradio as gr

import auth
import styles
from sidekick import Sidekick

LAUNCH_STYLE = {"theme": styles.THEME, "css": styles.CSS, "head": styles.JS}

HEADER = """
<div id="header">
    <div class="context-label">Your personal co-worker</div>
    <h1>Sidekick</h1>
    <div class="brand-bar"></div>
</div>
"""


def render_todos(todos):
    if not todos:
        items = '<div class="placeholder">The Sidekick will write its plan here as it works</div>'
    else:
        items = "<ul>" + "".join(
            f'<li class="{todo["status"]}"><span class="mark"></span>{html.escape(todo["content"])}</li>'
            for todo in todos
        ) + "</ul>"
    return f"<h3>Plan</h3>{items}"


async def login(username, password):
    """The Sidekick (and its browser) only starts after a successful login."""
    if not await asyncio.to_thread(auth.verify_user, username, password):
        await asyncio.sleep(1)  # slow down password guessing
        return None, gr.update(), gr.update(), "Wrong username or password.", gr.update()
    new_sidekick = Sidekick()
    await new_sidekick.setup()
    return new_sidekick, gr.update(visible=False), gr.update(visible=True), "", gr.update(interactive=True)


async def register(username, password, confirm, code):
    return await asyncio.to_thread(auth.register_user, username, password, confirm, code)


def logout(sidekick):
    if sidekick:
        sidekick.cleanup()
    return None, gr.update(visible=True), gr.update(visible=False), gr.update(interactive=False)


async def process_message(sidekick, message, success_criteria, history):
    if sidekick is None:  # the user clicked before setup finished bringing up the MCP servers
        return history, gr.update(visible=False), sidekick
    results = await sidekick.run_turn(message, success_criteria, history)
    return results, gr.update(visible=sidekick.paused), sidekick


async def approve(sidekick, history):
    results = await sidekick.resume(history)
    return results, gr.update(visible=sidekick.paused), sidekick


def watch_todos(sidekick):
    """Called by the timer. The timer is the plan panel's only writer: if a long-running
    event owned the panel as an output, Gradio would lock it as pending and live updates
    would not render while the Sidekick works."""
    return render_todos(sidekick.todos) if sidekick else render_todos([])


async def reset(sidekick):
    if sidekick:
        sidekick.cleanup()
    new_sidekick = Sidekick()
    await new_sidekick.setup()
    return "", "", None, gr.update(visible=False), new_sidekick


def free_resources(sidekick):
    if sidekick:
        sidekick.cleanup()


with gr.Blocks(title="Sidekick") as ui:
    gr.HTML(HEADER)
    sidekick = gr.State(delete_callback=free_resources)

    with gr.Column(visible=True) as login_panel:
        with gr.Tabs():
            with gr.Tab("Log in"):
                login_user = gr.Textbox(label="Username")
                login_pass = gr.Textbox(label="Password", type="password")
                login_button = gr.Button("Log in", variant="primary")
                login_message = gr.Markdown()
            with gr.Tab("Register"):
                reg_user = gr.Textbox(label="Choose a username")
                reg_pass = gr.Textbox(label="Choose a password (8+ characters)", type="password")
                reg_confirm = gr.Textbox(label="Repeat the password", type="password")
                reg_code = gr.Textbox(label="Invite code", type="password")
                reg_button = gr.Button("Create account", variant="primary")
                reg_message = gr.Markdown()

    with gr.Column(visible=False) as app_panel:
        with gr.Row():
            chatbot = gr.Chatbot(label="Sidekick", height=320, scale=3, elem_id="chat")
            with gr.Column(scale=1):
                todos_panel = gr.HTML(render_todos([]), elem_id="plan-panel")
        with gr.Group(elem_id="ask-panel"):
            with gr.Row():
                message = gr.Textbox(show_label=False, placeholder="Your request to the Sidekick")
            with gr.Row():
                success_criteria = gr.Textbox(show_label=False, placeholder="What are your success criteria?")
        with gr.Row():
            reset_button = gr.Button("Reset", elem_id="reset-button")
            approve_button = gr.Button("Approve and continue", visible=False, elem_id="approve-button")
            go_button = gr.Button("Go!", elem_id="go-button", interactive=False)
            logout_button = gr.Button("Log out")

    timer = gr.Timer(1)

    login_button.click(login, [login_user, login_pass], [sidekick, login_panel, app_panel, login_message, go_button])
    login_pass.submit(login, [login_user, login_pass], [sidekick, login_panel, app_panel, login_message, go_button])
    reg_button.click(register, [reg_user, reg_pass, reg_confirm, reg_code], [reg_message])
    logout_button.click(logout, [sidekick], [sidekick, login_panel, app_panel, go_button])

    timer.tick(watch_todos, [sidekick], [todos_panel], show_progress="hidden")
    message.submit(process_message, [sidekick, message, success_criteria, chatbot],
                   [chatbot, approve_button, sidekick])
    success_criteria.submit(process_message, [sidekick, message, success_criteria, chatbot],
                            [chatbot, approve_button, sidekick])
    go_button.click(process_message, [sidekick, message, success_criteria, chatbot],
                    [chatbot, approve_button, sidekick])
    approve_button.click(approve, [sidekick, chatbot], [chatbot, approve_button, sidekick])
    reset_button.click(reset, [sidekick], [message, success_criteria, chatbot, approve_button, sidekick])


if __name__ == "__main__":
    # On Render, PORT is set for you and the app must listen on 0.0.0.0.
    # Users log in (or register with the invite code) inside the app itself.
    on_render = "PORT" in os.environ
    ui.launch(
        server_name="0.0.0.0" if on_render else "127.0.0.1",
        server_port=int(os.environ.get("PORT", 7860)),
        inbrowser=not on_render,
        **LAUNCH_STYLE,
    )
