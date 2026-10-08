"""Offline browser fixtures for the modern Creator Center publish controls."""

from unittest.mock import MagicMock

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from scripts.publish import PublishAction


@pytest.fixture
def local_page():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as exc:
            pytest.skip(f"local Chromium executable unavailable: {exc}")
        page = browser.new_page()
        try:
            yield page
        finally:
            browser.close()


def _action(page):
    client = MagicMock()
    client.page = page
    return PublishAction(client)


OLD_COVER = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
NEW_COVER = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/J9sAAAAASUVORK5CYII="


def _install_cover_editor(page, *, update_preview):
    preview_update = (
        f"preview.style.backgroundImage = \"url('{NEW_COVER}')\";"
        if update_preview
        else ""
    )
    page.set_content(
        """
        <div class="cover-plugin-preview"><div class="cover">
          <div class="default" style="width:120px;height:80px;background-image:url('__OLD_COVER__')"></div>
          <button>编辑封面</button>
        </div></div>
        <div class="mojito-container" style="display:none">
          <input type="file" accept="image/png, image/jpeg, image/*">
          <img id="selected" width="1" height="1" src="__OLD_COVER__">
          <button id="done" disabled>完成</button>
        </div>
        <script>
          const preview = document.querySelector('.default');
          const modal = document.querySelector('.mojito-container');
          const input = modal.querySelector('input');
          const selected = modal.querySelector('#selected');
          const done = modal.querySelector('#done');
          document.querySelector('.cover button').addEventListener('click', () => {
            modal.style.display = 'block';
          });
          input.addEventListener('change', () => {
            selected.src = '__NEW_COVER__';
            done.disabled = false;
          });
          done.addEventListener('click', () => {
            __PREVIEW_UPDATE__
            modal.style.display = 'none';
          });
        </script>
        """
        .replace("__OLD_COVER__", OLD_COVER)
        .replace("__NEW_COVER__", NEW_COVER)
        .replace("__PREVIEW_UPDATE__", preview_update)
    )


def test_local_fixture_requires_terminal_video_evidence(local_page):
    local_page.set_content(
        """
        <div class="upload-content" style="width:500px">
          <span>demo.mp4</span><span>重新上传</span><span>检测为高清视频</span>
        </div>
        """
    )

    state = _action(local_page)._video_completion_state("/tmp/demo.mp4")

    assert state["complete"] is True
    assert {"filename", "reupload", "hd_check"} <= set(state["markers"])

    local_page.locator(".upload-content").evaluate(
        """el => {
            el.innerHTML = '<span>demo.mp4</span>';
            document.body.insertAdjacentHTML('beforeend', '<span>重新上传</span>');
        }"""
    )
    stale_state = _action(local_page)._video_completion_state("/tmp/demo.mp4")
    assert stale_state["complete"] is False

    local_page.locator(".upload-content").evaluate(
        "el => el.insertAdjacentHTML('beforeend', '<span>处理中</span>')"
    )
    busy_state = _action(local_page)._video_completion_state("/tmp/demo.mp4")
    assert busy_state["complete"] is False
    assert busy_state["busy"] is True


def test_account_binding_waits_for_current_creator_topbar(local_page):
    local_page.set_content(
        """
        <main>目标账号</main>
        <script>setTimeout(() => {
          const topbar = document.createElement('div');
          topbar.className = 'd-topbar';
          topbar.innerHTML = '<div class="user-info"><span class="name-box">实际账号</span></div>';
          document.body.appendChild(topbar);
        }, 150);</script>
        """
    )
    action = _action(local_page)
    assert action._check_account_binding("实际账号")["account_ok"] is True
    assert action._check_account_binding("目标账号")["account_ok"] is False


def test_publish_tab_skips_hidden_duplicate(local_page):
    local_page.set_content(
        """
        <div class="creator-tab" style="display:none">上传视频</div>
        <div class="creator-tab" onclick="window.selectedTab='video'">上传视频</div>
        <button>上传视频</button>
        """
    )
    _action(local_page)._click_publish_tab("上传视频")
    assert local_page.evaluate("window.selectedTab") == "video"


def test_local_fixture_reads_tiptap_body_and_rendered_cover(local_page):
    local_page.set_content(
        """
        <header><span class="account-name">测试账号</span></header>
        <div class="d-input"><input class="title" value="精确标题"></div>
        <div contenteditable="true">第一行<br><br>第二行</div>
        <div class="permission-card-wrapper">
          <div class="d-select-content">公开可见</div>
          <div style="display:none">仅自己可见</div>
        </div>
        <div class="cover-plugin-preview"><div class="cover">
          <div class="default" style="width:120px;height:80px;background-image:url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')"></div>
        </div></div>
        <style>xhs-publish-btn { display:block; width:220px; height:40px; }</style>
        <xhs-publish-btn is-publish="true" submit-disabled="false"></xhs-publish-btn>
        <script>
          customElements.define('xhs-publish-btn', class extends HTMLElement {
            connectedCallback() {
              this.style.display = 'inline-block';
              this.style.width = '220px'; this.style.height = '40px';
              const root = this.attachShadow({mode: 'closed'});
              root.innerHTML = '<button>保存</button><button>发布</button>';
            }
          });
        </script>
        """
    )
    action = _action(local_page)

    assert action._read_content() == "第一行\n第二行"
    ready = action._check_publish_ready(
        expected_title="精确标题",
        expected_content="第一行\n\n第二行",
        expected_account="测试账号",
        expected_visibility="公开可见",
        require_cover=True,
    )

    assert ready["content_ok"] is True
    assert ready["cover_ok"] is True
    assert ready["visibility_ok"] is True
    assert ready["account_ok"] is True
    assert ready["publish_button_ready"] is True


@pytest.mark.parametrize("save_label", ["保存", "暂存离开"])
def test_local_fixture_reopens_exact_draft_card_after_widget_save(local_page, save_label):
    local_page.set_content(
        """
        <div id="draft-nav">草稿箱(1)</div>
        <div id="drafts" style="display:none">
          <article class="draft-card"><span>精确标题</span><button>编辑</button></article>
        </div>
        <div class="d-input"><input class="title" value=""></div>
        <div contenteditable="true"></div>
        <div class="cover-plugin-preview"><div class="cover">
          <div class="default" style="width:120px;height:80px;background-image:url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')"></div>
        </div></div>
        <style>xhs-publish-btn { display:block; width:220px; height:40px; }</style>
        <xhs-publish-btn is-publish="true" submit-disabled="false"></xhs-publish-btn>
        <script>
          customElements.define('xhs-publish-btn', class extends HTMLElement {
            connectedCallback() {
              this.style.display = 'inline-block';
              this.style.width = '220px'; this.style.height = '40px';
              const root = this.attachShadow({mode: 'closed'});
              root.innerHTML = '<style>button{width:110px;height:40px}</style><button id="publish">发布</button><button id="save">保存</button>';
              root.querySelector('#publish').addEventListener('click', () => {
                window.__clickedLabel = '发布';
              });
              root.querySelector('#save').addEventListener('click', () => {
                window.__clickedLabel = '保存';
                document.querySelector('#drafts').style.display = 'block';
              });
            }
          });
          document.querySelector('.draft-card button').addEventListener('click', () => {
            document.querySelector('.title').value = '精确标题';
            document.querySelector('[contenteditable]').innerText = '正文\\n\\n#历史';
          });
        </script>
        """.replace("保存", save_label)
    )
    action = _action(local_page)
    result = action._save_draft(
        "精确标题", expected_body="正文\n\n#历史", require_cover=True, timeout=2
    )

    assert result["draft_title_exact"] is True
    assert result["body_ok"] is True
    assert result["cover_readback"]["cover_ok"] is True
    assert local_page.evaluate("window.__clickedLabel") == save_label


def test_local_fixture_fails_when_shadow_widget_has_no_save_control(local_page):
    local_page.set_content(
        """
        <xhs-publish-btn></xhs-publish-btn>
        <script>
          customElements.define('xhs-publish-btn', class extends HTMLElement {
            connectedCallback() {
              const root = this.attachShadow({mode: 'closed'});
              root.innerHTML = '<button>发布</button>';
            }
          });
        </script>
        """
    )
    with pytest.raises(RuntimeError, match="保存按钮"):
        _action(local_page)._save_draft("标题", expected_body="正文", timeout=1)


def test_local_fixture_cover_requires_new_decoded_preview(local_page, tmp_path):
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"cover")

    _install_cover_editor(local_page, update_preview=True)
    updated = _action(local_page)._set_cover(str(cover), timeout=2)
    assert updated["cover_ok"] is True
    assert updated["cover_source"] == NEW_COVER


def test_local_fixture_cover_rejects_unchanged_preview(local_page, tmp_path):
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"cover")
    _install_cover_editor(local_page, update_preview=False)
    with pytest.raises(RuntimeError, match="来源未发生变化"):
        _action(local_page)._set_cover(str(cover), timeout=2)


@pytest.mark.parametrize("source,kind", [
    ("blob:https://example.test/local", "local"),
    ("https://example.test/video.mp4", "remote"),
])
def test_preview_evidence_does_not_confuse_local_and_remote(local_page, source, kind):
    local_page.set_content('<video style="width:100px;height:100px"></video>')
    local_page.locator("video").evaluate("""(el, src) => {
        Object.defineProperty(el, 'currentSrc', {value: src});
        Object.defineProperty(el, 'readyState', {value: 2});
        Object.defineProperty(el, 'duration', {value: 10});
    }""", source)
    result = _action(local_page)._video_preview_status()
    assert result["preview_source"] == kind
    assert result[f"{kind}_preview"] == "available"
    other = "remote" if kind == "local" else "local"
    assert result[f"{other}_preview"] == "not_observed"
