"""
小红书发布模块（图文 + 视频）

Reference: xiaohongshu-mcp/publish.go + publish_video.go (Apache-2.0). See THIRD_PARTY_NOTICES.md.
安全发布校验（人工确认 checkpoint）
"""

import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from ._utils import is_element_blocked
from .client import CAPTCHA_URL_PATTERNS, DEFAULT_COOKIE_PATH, XiaohongshuClient
from .selectors import get_selector_contract

PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
PUBLISH_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")
PUBLISH_STATUS_CONFIRMED = "confirmed"
PUBLISH_STATUS_SUBMITTED_UNCONFIRMED = "submitted_unconfirmed"
PUBLISH_STATUS_FAILED = "failed"
PUBLISH_STATUS_DRAFT_SAVED = "draft_saved"
TITLE_LENGTH_WARNING_THRESHOLD = 20
SCHEDULE_FORMAT = "%Y-%m-%d %H:%M"
MIN_SCHEDULE_DELAY = timedelta(hours=1)
MAX_SCHEDULE_DELAY = timedelta(days=14)
LOGIN_URL_MARKERS = ("/login", "passport", "signin")
TRUSTED_CONFIRMATION_HOSTS = ("creator.xiaohongshu.com",)
FAILED_DESTINATION_MARKERS = ("/error", "/404", "/500", "/maintenance")
CONTENT_EDITOR_SELECTOR = get_selector_contract("publish.content_editor").primary
VIDEO_COMPLETION_MARKER_SELECTORS = get_selector_contract(
    "publish.video_completion_marker"
).selectors
COVER_TRIGGER_SELECTOR = get_selector_contract("publish.cover_trigger").primary
COVER_EDIT_BUTTON_SELECTOR = get_selector_contract("publish.cover_edit_button").primary
COVER_FILE_INPUT_SELECTOR = get_selector_contract("publish.cover_file_input").primary
COVER_COMPLETE_BUTTON_SELECTOR = get_selector_contract(
    "publish.cover_complete_button"
).primary
DRAFT_BOX_SELECTOR = get_selector_contract("publish.draft_box").primary
DRAFT_SAVE_LABELS = frozenset(
    get_selector_contract("publish.draft_save_control").selectors
)
ACCOUNT_HEADER_SELECTORS = get_selector_contract("publish.account_header").selectors


@dataclass(frozen=True)
class PublishConfirmation:
    """Result of clicking publish and observing the browser afterwards."""

    status: str
    message: str
    signal: str
    url: str = ""

    @property
    def success(self) -> bool:
        """Only an observed confirmation signal counts as success."""
        return self.status == PUBLISH_STATUS_CONFIRMED


@dataclass(frozen=True)
class PublishValidation:
    """Validated local inputs and non-blocking platform-limit warnings."""

    schedule_at: Optional[datetime]
    warnings: tuple[str, ...]
    media_paths: tuple[str, ...] = ()


def _normalize_now(now: Optional[datetime]) -> datetime:
    """Return ``now`` in the platform scheduling timezone."""
    if now is None:
        return datetime.now(PUBLISH_TIMEZONE)
    if now.tzinfo is None:
        return now.replace(tzinfo=PUBLISH_TIMEZONE)
    return now.astimezone(PUBLISH_TIMEZONE)


def validate_schedule_time(
    schedule_time: Optional[str],
    *,
    now: Optional[datetime] = None,
) -> Optional[datetime]:
    """Validate a scheduled publish time in Asia/Shanghai.

    Scheduled publishing accepts the local format ``YYYY-MM-DD HH:MM`` and
    must be between one hour and fourteen days from ``now``, inclusively.
    """
    if schedule_time is None:
        return None
    if (
        not isinstance(schedule_time, str)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", schedule_time) is None
    ):
        raise ValueError(f"定时发布时间格式应为 {SCHEDULE_FORMAT}")

    try:
        parsed = datetime.strptime(schedule_time, SCHEDULE_FORMAT).replace(
            tzinfo=PUBLISH_TIMEZONE,
        )
    except ValueError as exc:
        raise ValueError(f"定时发布时间格式应为 {SCHEDULE_FORMAT}") from exc

    delta = parsed - _normalize_now(now)
    if delta < MIN_SCHEDULE_DELAY or delta > MAX_SCHEDULE_DELAY:
        raise ValueError("定时发布时间必须在当前时间 1 小时至 14 天之间（Asia/Shanghai）")
    return parsed


def validate_media_paths(media_paths: List[str]) -> tuple[str, ...]:
    """Require every local media path to be a readable regular file."""
    if not media_paths:
        raise ValueError("至少需要一个媒体文件")

    validated = []
    for raw_path in media_paths:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            raise ValueError(f"媒体文件不存在或不是普通文件: {raw_path}")
        try:
            with path.open("rb"):
                pass
        except OSError as exc:
            raise ValueError(f"媒体文件不可读: {raw_path}") from exc
        validated.append(str(path.resolve()))
    return tuple(validated)


def validate_publish_request(
    *,
    title: str,
    media_paths: Optional[List[str]] = None,
    schedule_time: Optional[str] = None,
    now: Optional[datetime] = None,
) -> PublishValidation:
    """Validate stable local requirements before opening the publish page."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("标题不能为空")
    validated_media = validate_media_paths(media_paths) if media_paths is not None else ()

    warnings = []
    if len(title) > TITLE_LENGTH_WARNING_THRESHOLD:
        warnings.append(
            f"标题长度为 {len(title)}，超过当前建议的 {TITLE_LENGTH_WARNING_THRESHOLD} 字；"
            "平台限制可能变化，请在发布页复核"
        )

    schedule_at = validate_schedule_time(schedule_time, now=now)
    return PublishValidation(
        schedule_at=schedule_at,
        warnings=tuple(warnings),
        media_paths=validated_media,
    )


@dataclass
class PublishImageContent:
    """发布图文内容数据类（对应 Go publish.go PublishImageContent struct）"""
    title: str = ""
    content: str = ""
    image_paths: List[str] = field(default_factory=list)
    tags: Optional[List[str]] = None
    schedule_time: Optional[str] = None
    is_original: bool = False       # 是否声明原创
    visibility: str = "公开可见"     # 可见范围: 公开可见/仅自己可见/仅互关好友可见
    video_path: Optional[str] = None  # 视频发布时使用


class PublishAction:
    """发布动作"""

    def __init__(self, client: XiaohongshuClient):
        self.client = client

    @staticmethod
    def _normalize_editor_text(value: Any) -> str:
        """Normalize browser line endings without rewriting body text."""
        if not isinstance(value, str):
            return ""
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        return re.sub(r"\n+", "\n", normalized)

    @staticmethod
    def _compose_expected_body(content: str, tags: Optional[List[str]]) -> str:
        """Build the exact body expected after deterministic hashtag append."""
        body = content or ""
        clean_tags = [tag.lstrip("#").strip() for tag in (tags or [])[:10]]
        clean_tags = [tag for tag in clean_tags if tag]
        if not clean_tags:
            return body
        suffix = " ".join(f"#{tag}" for tag in clean_tags)
        return f"{body.rstrip(chr(10))}\n\n{suffix}" if body else suffix

    @staticmethod
    def _is_visible(locator) -> bool:
        """Read visibility from a Playwright locator without trusting mocks."""
        try:
            return locator.count() > 0 and locator.first.is_visible() is True
        except Exception:
            return False

    def _content_editor(self):
        """Return the unique modern body editor, with legacy fallbacks."""
        page = self.client.page
        selectors = (
            CONTENT_EDITOR_SELECTOR,
            *get_selector_contract("publish.content_editor").fallbacks,
        )
        for selector in selectors:
            try:
                editor = page.locator(selector)
                if editor.count() == 1:
                    return editor.first
                if editor.count() > 1 and selector == CONTENT_EDITOR_SELECTOR:
                    # A body editor must be unambiguous.  Do not bind a title,
                    # hidden editor, or stale draft node by guessing.
                    continue
            except Exception:
                continue
        return None

    def _read_content(self) -> str:
        """Read the body editor while preserving all non-newline characters."""
        editor = self._content_editor()
        if editor is None:
            return ""
        for reader in ("inner_text", "text_content", "input_value"):
            try:
                value = getattr(editor, reader)()
                normalized = self._normalize_editor_text(value)
                if normalized:
                    return normalized
            except Exception:
                continue
        return ""

    def _video_completion_state(self, video_path: str) -> Dict[str, Any]:
        """Return upload completion evidence from the current page."""
        page = self.client.page
        filename = os.path.basename(video_path)
        uploader = None
        try:
            candidates = page.locator(
                ".upload-content, .upload-video, [class*='video-upload'], [class*='upload-video']"
            ).filter(has_text=filename)
            candidate_count = candidates.count()
            if candidate_count != 1:
                return {
                    "complete": False,
                    "markers": [],
                    "busy": False,
                    "terminal": False,
                    "reason": "uploader_scope_missing_or_ambiguous",
                }
            uploader = candidates.first
        except Exception:
            return {
                "complete": False,
                "markers": [],
                "busy": False,
                "terminal": False,
                "reason": "uploader_scope_unavailable",
            }

        # Prefer evidence inside the uploader containing this filename.  A
        # stale preview or another upload on the page must not complete this
        # upload by supplying an unrelated terminal marker.
        scope = uploader
        markers: list[str] = []
        marker_queries = (
            ("filename", filename),
            ("reupload", VIDEO_COMPLETION_MARKER_SELECTORS[1]),
            ("hd_check", VIDEO_COMPLETION_MARKER_SELECTORS[2]),
        )
        for name, query in marker_queries:
            try:
                locator = (
                    scope.get_by_text(filename, exact=True)
                    if name == "filename"
                    else scope.locator(query)
                )
                if self._is_visible(locator):
                    markers.append(name)
            except Exception:
                continue

        # Terminal labels and the filename must belong to the current upload.
        # Scope progress checks to the nearest uploader rather than treating a
        # page-level busy widget as evidence that this video is still busy.
        terminal = "reupload" in markers or "hd_check" in markers
        busy = False
        try:
            scope_text = scope.inner_text()
        except Exception:
            scope_text = ""
        if re.search(r"上传中|处理中|取消上传", scope_text or ""):
            busy = True
        if not busy:
            for selector in (
                '[aria-busy="true"]',
                ".uploading",
                ".upload-progress",
                ".progress-bar",
            ):
                try:
                    scoped = scope.locator(selector)
                    if self._is_visible(scoped):
                        busy = True
                        break
                except Exception:
                    continue
        return {
            "complete": "filename" in markers and terminal and not busy,
            "markers": markers,
            "busy": busy,
            "terminal": terminal,
        }

    def _check_account_binding(self, expected_account: Optional[str]) -> Dict[str, Any]:
        """Verify an expected account from Creator Center header evidence."""
        if not expected_account:
            return {"expected_account": None, "account_ok": True}
        page = self.client.page
        observed: list[str] = []
        try:
            for selector in ACCOUNT_HEADER_SELECTORS:
                loc = page.locator(selector)
                for index in range(loc.count()):
                    item = loc.nth(index)
                    if item.is_visible() is True:
                        text = item.inner_text()
                        if isinstance(text, str):
                            observed.append(text.strip())
        except Exception:
            pass
        matched = any(expected_account == value for value in observed)
        return {
            "expected_account": expected_account,
            "observed_account": expected_account if matched else None,
            "account_ok": matched,
        }

    def _navigate_to_publish(self):
        """导航到创作者中心发布页"""
        print("打开创作者中心发布页...", file=sys.stderr)
        self.client.navigate(PUBLISH_URL)
        time.sleep(3)

    def _click_publish_tab(self, tab_name: str):
        """点击发布类型 TAB（上传图文 / 上传视频）

        Go 参考: publish.go:119-153 mustClickPublishTab + getTabElement
        增加遮挡检测（isElementBlocked），被遮挡时 removePopCover + clickEmptyPosition。
        """
        page = self.client.page

        # 等待上传区域出现
        try:
            page.wait_for_selector('div.upload-content, div.creator-tab', timeout=15000)
        except Exception:
            print("等待发布页加载超时，继续尝试", file=sys.stderr)

        time.sleep(1)

        # 移除可能的弹窗遮挡
        page.evaluate("""() => {
            var popover = document.querySelector('div.d-popover');
            if (popover) popover.remove();
        }""")

        # 带遮挡检测和重试的 TAB 点击
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                tabs = page.locator('div.creator-tab')
                for i in range(tabs.count()):
                    tab = tabs.nth(i)
                    text = tab.text_content().strip()
                    if text != tab_name:
                        continue

                    # 检测遮挡
                    try:
                        blocked = is_element_blocked(page, tab)
                    except Exception:
                        blocked = False

                    if blocked:
                        print("发布 TAB 被遮挡，移除弹窗后重试", file=sys.stderr)
                        # removePopCover: 移除弹窗
                        page.evaluate("""() => {
                            var popover = document.querySelector('div.d-popover');
                            if (popover) popover.remove();
                        }""")
                        # clickEmptyPosition: 点击空位置消除焦点
                        x = 380 + random.randint(0, 100)
                        y = 20 + random.randint(0, 60)
                        page.mouse.click(x, y)
                        time.sleep(0.3)
                        break  # 重新扫描

                    tab.click()
                    time.sleep(1)
                    print(f"已切换到「{tab_name}」", file=sys.stderr)
                    return
            except Exception as e:
                print(f"查找 TAB 出错: {e}", file=sys.stderr)

            time.sleep(0.2)

        # 回退：使用文本定位
        try:
            page.get_by_text(tab_name, exact=True).click()
            time.sleep(1)
            print(f"已切换到「{tab_name}」(回退)", file=sys.stderr)
        except Exception as e:
            print(f"切换 TAB「{tab_name}」失败: {e}", file=sys.stderr)

    def _upload_images(self, image_paths: List[str]):
        """逐张上传图片"""
        page = self.client.page
        valid_paths = [p for p in image_paths if os.path.exists(p)]

        if not valid_paths:
            raise ValueError("没有有效的图片文件")

        for i, path in enumerate(valid_paths):
            abs_path = os.path.abspath(path)
            print(f"上传图片 ({i+1}/{len(valid_paths)}): {abs_path}", file=sys.stderr)

            # 第一张用 .upload-input，后续用 input[type=file]
            selector = '.upload-input' if i == 0 else 'input[type="file"]'
            try:
                upload_input = page.locator(selector)
                upload_input.set_input_files(abs_path)
            except Exception:
                # 回退
                upload_input = page.locator('input[type="file"]')
                upload_input.set_input_files(abs_path)

            # 等待图片上传完成（预览元素出现）
            expected = i + 1
            for _ in range(120):  # 最多等 60 秒
                try:
                    previews = page.locator('.img-preview-area .pr, .upload-preview-item')
                    if previews.count() >= expected:
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            time.sleep(1)

        print(f"全部 {len(valid_paths)} 张图片上传完成", file=sys.stderr)

    def _upload_video(self, video_path: str, timeout: float = 600):
        """上传视频文件"""
        page = self.client.page

        if not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")

        abs_path = os.path.abspath(video_path)
        print(f"上传视频: {abs_path}", file=sys.stderr)

        try:
            upload_input = page.locator('.upload-input')
            upload_input.set_input_files(abs_path)
        except Exception:
            upload_input = page.locator('input[type="file"]')
            upload_input.set_input_files(abs_path)

        # The upload page now exposes completion through the filename and
        # processing labels while the publish control lives in a closed-shadow
        # xhs-publish-btn.  Never infer readiness from the old red button.
        print("等待视频处理完成...", file=sys.stderr)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self._video_completion_state(video_path)
            if state["complete"]:
                print(
                    f"视频处理完成，依据: {','.join(state['markers'])}",
                    file=sys.stderr,
                )
                return state
            time.sleep(1)

        raise TimeoutError(f"等待视频处理完成超时（{timeout:g} 秒）")

    def _fill_title(self, title: str):
        """填写标题"""
        page = self.client.page
        try:
            title_input = page.locator('div.d-input input')
            title_input.first.fill(title)

            # 检查标题是否超长
            max_suffix = page.locator('div.title-container div.max_suffix')
            if max_suffix.count() > 0 and max_suffix.is_visible():
                length_text = max_suffix.text_content()
                print(f"警告: 标题超长 ({length_text})", file=sys.stderr)

            print(f"标题已填写: {title}", file=sys.stderr)
        except Exception as e:
            print(f"填写标题失败: {e}", file=sys.stderr)

    def _fill_content(self, content: str):
        """填写正文"""
        page = self.client.page

        content_el = self._content_editor()

        if content_el is None:
            print("未找到正文输入框", file=sys.stderr)
            return

        try:
            content_el.click()
            content_el.fill(content)

            readback = self._read_content()
            expected = self._normalize_editor_text(content)
            if readback != expected:
                print("正文已写入，但读回内容未能确认绑定", file=sys.stderr)

            # 检查正文是否超长
            length_error = page.locator('div.edit-container div.length-error')
            if length_error.count() > 0 and length_error.is_visible():
                err_text = length_error.text_content()
                print(f"警告: 正文超长 ({err_text})", file=sys.stderr)

            print("正文已填写", file=sys.stderr)
        except Exception as e:
            print(f"填写正文失败: {e}", file=sys.stderr)

    def _input_tags(self, tags: List[str]):
        """Append exact safe hashtag text while preserving the existing body."""
        if not tags:
            return

        content_el = self._content_editor()
        if content_el is None:
            return

        clean_tags = [tag.lstrip("#").strip() for tag in tags[:10] if tag.lstrip("#").strip()]
        if not clean_tags:
            return
        body = self._read_content()
        if not body:
            raise RuntimeError("无法读回正文，拒绝追加标签")
        suffix = " ".join(f"#{tag}" for tag in clean_tags)
        combined = f"{body.rstrip(chr(10))}\n\n{suffix}" if body else suffix
        try:
            content_el.fill(combined)
            readback = self._read_content()
            if (
                not readback
                or not readback.startswith(self._normalize_editor_text(body))
                or not readback.endswith(suffix)
            ):
                raise RuntimeError("正文绑定读回失败，拒绝覆盖正文")
            print(f"已按原文追加 {len(clean_tags)} 个标签", file=sys.stderr)
        except Exception as exc:
            print(f"追加标签失败: {exc}", file=sys.stderr)
            raise

    def _set_visibility(self, page, visibility: str):
        """设置可见范围

        Go 参考: publish.go:792-836 setVisibility
        支持: "公开可见"(默认), "仅自己可见", "仅互关好友可见"
        """
        if not visibility or visibility == "公开可见":
            print("可见范围使用默认：公开可见", file=sys.stderr)
            return

        supported = {"仅自己可见", "仅互关好友可见"}
        if visibility not in supported:
            raise ValueError(
                f"不支持的可见范围: {visibility}，支持: 公开可见、仅自己可见、仅互关好友可见"
            )

        # 点击可见范围下拉框
        dropdown = page.locator("div.permission-card-wrapper div.d-select-content")
        dropdown.click()
        time.sleep(0.5)

        # 在下拉选项中查找并点击目标
        opts = page.locator("div.d-options-wrapper div.d-grid-item div.custom-option")
        for i in range(opts.count()):
            opt = opts.nth(i)
            text = opt.text_content()
            if visibility in text:
                opt.click()
                print(f"已设置可见范围: {visibility}", file=sys.stderr)
                time.sleep(0.2)
                return

        raise ValueError(f"未找到可见范围选项: {visibility}")

    def _confirm_original_declaration(self, page):
        """处理原创声明确认弹窗

        Go 参考: publish.go:952-1034 confirmOriginalDeclaration
        使用 JS 查找 footer 中的 checkbox 和声明原创按钮。
        """
        time.sleep(0.8)

        # 查找弹窗 footer 并勾选 checkbox
        result = page.evaluate("""
            () => {
                const footers = document.querySelectorAll('div.footer');
                for (const footer of footers) {
                    if (!footer.textContent.includes('原创声明须知')) {
                        continue;
                    }
                    const checkbox = footer.querySelector('div.d-checkbox input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) {
                        checkbox.click();
                        console.log('已勾选原创声明须知 checkbox');
                    }
                    return 'found_footer';
                }
                return 'footer_not_found';
            }
        """)
        if result == "footer_not_found":
            print("警告: 未找到原创声明确认弹窗的 footer", file=sys.stderr)

        time.sleep(0.5)

        # 点击「声明原创」按钮
        result2 = page.evaluate("""
            () => {
                const footers = document.querySelectorAll('div.footer');
                for (const footer of footers) {
                    if (!footer.textContent.includes('声明原创')) {
                        continue;
                    }
                    const btn = footer.querySelector('button.custom-button');
                    if (btn) {
                        if (btn.classList.contains('disabled') || btn.disabled) {
                            const checkbox = footer.querySelector('div.d-checkbox input[type="checkbox"]');
                            if (checkbox && !checkbox.checked) {
                                checkbox.click();
                            }
                            return 'button_disabled';
                        }
                        btn.click();
                        return 'clicked';
                    }
                }
                return 'button_not_found';
            }
        """)

        status = result2
        print(f"原创声明确认结果: {status}", file=sys.stderr)

        if status == "button_not_found":
            print("警告: 未找到声明原创按钮", file=sys.stderr)
        elif status == "button_disabled":
            print("警告: 声明原创按钮仍处于禁用状态", file=sys.stderr)
        else:
            print("已成功点击声明原创按钮", file=sys.stderr)

        time.sleep(0.3)

    def _set_original(self, page):
        """设置原创声明

        Go 参考: publish.go:889-949 setOriginal
        在 div.custom-switch-card 中查找包含"原创声明"文本的卡片，
        检查 d-switch 开关状态，未勾选则点击并处理确认弹窗。
        """
        # 查找包含"原创声明"文本的 custom-switch-card
        switch_cards = page.locator("div.custom-switch-card")
        for i in range(switch_cards.count()):
            card = switch_cards.nth(i)
            text = card.text_content()

            if "原创声明" not in text:
                continue

            # 找到其中 d-switch
            switch_elem = card.locator("div.d-switch")
            if switch_elem.count() == 0:
                continue

            # 检查是否已勾选
            checked = switch_elem.evaluate("""(el) => {
                const input = el.querySelector('input[type="checkbox"]');
                return input ? input.checked : false;
            }""")
            if checked:
                print("原创声明已开启，跳过", file=sys.stderr)
                return

            # 点击开关
            switch_elem.click()
            time.sleep(0.5)

            # 处理确认弹窗
            self._confirm_original_declaration(page)
            print("已开启原创声明", file=sys.stderr)
            return

        print("提示: 未找到原创声明选项（可能账号不支持）", file=sys.stderr)

    def _set_schedule(self, schedule_time: str):
        """设置定时发布（格式: 2025-01-01 12:00）"""
        page = self.client.page
        try:
            # 点击定时发布开关
            switch = page.locator('.post-time-wrapper .d-switch')
            switch.click()
            time.sleep(0.8)

            # 设置日期时间
            date_input = page.locator('.date-picker-container input')
            date_input.fill('')
            date_input.fill(schedule_time)
            time.sleep(0.5)

            print(f"定时发布设置: {schedule_time}", file=sys.stderr)
        except Exception as e:
            print(f"设置定时发布失败: {e}", file=sys.stderr)
            raise RuntimeError("设置定时发布失败，已阻止继续发布") from e

    def _set_cover(self, cover_path: str, timeout: float = 30) -> Dict[str, Any]:
        """Set a video cover through the native editor and verify it closes."""
        page = self.client.page
        if not os.path.isfile(cover_path):
            raise ValueError(f"封面文件不存在: {cover_path}")

        trigger = page.locator(COVER_TRIGGER_SELECTOR)
        if not self._is_visible(trigger):
            raise RuntimeError("未找到可编辑的视频封面预览")
        before = self._cover_readback()
        before_source = before.get("cover_source")
        trigger.first.hover()
        edit_button = page.locator(COVER_EDIT_BUTTON_SELECTOR)
        if not self._is_visible(edit_button):
            raise RuntimeError("未找到精确的编辑封面按钮")
        edit_button.first.click()

        modal = page.locator(".mojito-container")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._is_visible(modal):
            time.sleep(0.2)
        if not self._is_visible(modal):
            raise TimeoutError("打开封面编辑器超时")

        file_input = page.locator(COVER_FILE_INPUT_SELECTOR)
        if file_input.count() == 0:
            raise RuntimeError("封面编辑器未提供原生图片上传控件")
        file_input.first.set_input_files(os.path.abspath(cover_path))

        # The editor must decode the newly selected image before completion is
        # allowed.  A visible input or an unchanged old thumbnail is not proof
        # that the native editor accepted the file.
        selected = None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            selected = self._cover_modal_readback()
            if selected.get("decoded") and selected.get("source"):
                if not before_source or selected["source"] != before_source:
                    break
            time.sleep(0.2)
        if not selected or not selected.get("decoded") or not selected.get("source"):
            raise TimeoutError("封面编辑器未读回已解码的新图片")
        if before_source and selected["source"] == before_source:
            raise RuntimeError("封面编辑器仍显示旧图片，已停止")

        complete = page.locator(COVER_COMPLETE_BUTTON_SELECTOR)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self._is_visible(complete) and complete.first.is_enabled() is True:
                    complete.first.click()
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            raise TimeoutError("封面解析未完成，已停止，不会自动重新上传视频")

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._is_visible(modal):
                evidence = self._cover_readback()
                if not evidence["cover_ok"]:
                    raise RuntimeError("封面编辑器已关闭，但未读回渲染后的封面")
                after_source = evidence.get("cover_source")
                if not after_source or (before_source and after_source == before_source):
                    raise RuntimeError("封面编辑器关闭后封面来源未发生变化")
                print("视频封面已更新", file=sys.stderr)
                return {
                    "cover_path": os.path.abspath(cover_path),
                    **evidence,
                }
            time.sleep(0.2)
        raise TimeoutError("封面编辑器未关闭，已停止，不会自动重新上传视频")

    def _cover_modal_readback(self) -> Dict[str, Any]:
        """Read one visible, decoded image selected inside the cover modal."""
        page = self.client.page
        try:
            state = page.evaluate(
                """() => {
                    const modal = document.querySelector('.mojito-container');
                    if (!modal) return {decoded: false, source: ''};
                    const visible = element => {
                        const style = getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 &&
                            style.display !== 'none' && style.visibility !== 'hidden';
                    };
                    const image = Array.from(modal.querySelectorAll('img')).find(
                        item => visible(item) && item.complete && item.naturalWidth > 0 && item.src
                    );
                    return image
                        ? {decoded: true, source: image.currentSrc || image.src}
                        : {decoded: false, source: ''};
                }"""
            )
        except Exception:
            return {"decoded": False, "source": ""}
        return state if isinstance(state, dict) else {"decoded": False, "source": ""}

    def _cover_readback(self) -> Dict[str, Any]:
        """Read the rendered cover background, excluding unrelated modal images."""
        page = self.client.page
        try:
            preview = page.locator(COVER_TRIGGER_SELECTOR)
        except Exception:
            return {"cover_ok": False, "cover_readback": "missing_preview"}
        if not self._is_visible(preview):
            return {"cover_ok": False, "cover_readback": "missing_preview"}
        try:
            readback = preview.evaluate(
                r"""async el => {
                    const nodes = [el, el.closest('.cover')].filter(Boolean);
                    for (const node of nodes) {
                        const style = getComputedStyle(node);
                        const value = style.backgroundImage || node.style.backgroundImage || '';
                        if (!value || value === 'none') continue;
                        const match = value.match(/url\(["']?(.*?)["']?\)/);
                        if (!match) continue;
                        const source = new URL(match[1], document.baseURI).href;
                        const existing = Array.from(document.images).find(
                            image => image.currentSrc === source || image.src === source
                        );
                        if (existing && existing.complete) {
                            return {
                                background: value,
                                source,
                                loaded: existing.naturalWidth > 0,
                            };
                        }
                        const loaded = await new Promise(resolve => {
                            const image = new Image();
                            const finish = value => {
                                clearTimeout(timer);
                                resolve(value);
                            };
                            const timer = setTimeout(() => finish(false), 2000);
                            image.onload = () => finish(image.naturalWidth > 0);
                            image.onerror = () => finish(false);
                            image.src = source;
                            if (image.complete) finish(image.naturalWidth > 0);
                        });
                        return {background: value, source, loaded};
                    }
                    return {background: '', loaded: false};
                }"""
            )
        except Exception:
            readback = None
        if isinstance(readback, dict):
            background = readback.get("background", "")
            loaded = readback.get("loaded") is True
            source = readback.get("source") or ""
        else:
            background = ""
            loaded = False
            source = ""
        if isinstance(background, str) and "url(" in background and loaded:
            return {
                "cover_ok": True,
                "cover_readback": "background_image",
                "cover_source": source,
            }
        return {
            "cover_ok": False,
            "cover_readback": "background_not_loaded",
            "cover_source": source,
        }

    def _resume_draft(
        self,
        title: str,
        *,
        expected_body: Optional[str] = None,
        require_cover: bool = False,
        timeout: float = 15,
    ) -> Dict[str, Any]:
        """Open one exact draft card and verify its editor before mutations."""
        page = self.client.page
        draft_nav = page.get_by_text(re.compile(r"^草稿箱(?:\(\d+\))?$"))
        visible_navs = [
            draft_nav.nth(index)
            for index in range(draft_nav.count())
            if draft_nav.nth(index).is_visible()
        ]
        if visible_navs:
            if len(visible_navs) != 1:
                raise ValueError("草稿箱入口不唯一，拒绝恢复")
            visible_navs[0].click()
            time.sleep(0.5)

        title_matches = page.get_by_text(title, exact=True)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                visible_titles = [
                    title_matches.nth(index)
                    for index in range(title_matches.count())
                    if title_matches.nth(index).is_visible()
                ]
            except Exception:
                visible_titles = []
            visible_count = len(visible_titles)
            if visible_count:
                if visible_count != 1:
                    raise ValueError(f"草稿标题不唯一，拒绝恢复: {title}")
                try:
                    card = visible_titles[0].locator(
                        "xpath=ancestor::*[.//*[normalize-space(text())='编辑']][1]"
                    )
                    edit = card.get_by_text("编辑", exact=True)
                    if edit.count() != 1 or not self._is_visible(edit):
                        raise ValueError(f"草稿编辑入口不唯一: {title}")
                    edit.click()
                except ValueError:
                    raise
                except Exception as exc:
                    raise RuntimeError("无法定位精确草稿卡片的编辑入口") from exc
                time.sleep(0.5)
                break
            time.sleep(0.2)
        else:
            raise ValueError(f"未找到标题完全匹配的草稿: {title}")

        title_input = page.locator('div.d-input input').first
        try:
            readback = title_input.input_value()
        except Exception as exc:
            raise RuntimeError("恢复草稿后无法读回标题") from exc
        if readback != title:
            raise RuntimeError("恢复草稿标题读回不一致")
        body = self._read_content()
        body_ok = expected_body is None or (
            self._normalize_editor_text(body)
            == self._normalize_editor_text(expected_body)
        )
        if not body_ok:
            raise RuntimeError("恢复草稿正文与预期不一致，拒绝继续")
        cover = self._cover_readback()
        if require_cover and not cover["cover_ok"]:
            raise RuntimeError("恢复草稿未读回渲染后的封面，拒绝继续")
        return {
            "title": title,
            "title_ok": True,
            "body_ok": body_ok,
            "cover_readback": cover,
            "resume_draft": True,
        }

    def _click_shadow_save_control(self) -> Dict[str, Any]:
        """Click one semantically identified save button in the closed widget.

        The publish widget keeps its controls in a closed shadow root, so a
        normal locator cannot distinguish ``保存`` from ``发布``.  Chromium's
        DOM inspection protocol exposes the pierced tree for inspection; the
        final click is still performed on the resolved button object after a
        runtime check of its exact label, connected state, disabled state, and
        rendered visibility.
        """
        page = self.client.page
        try:
            cdp = page.context.new_cdp_session(page)
            tree = cdp.send(
                "DOM.getDocument", {"depth": -1, "pierce": True}
            ).get("root", {})
        except Exception as exc:
            raise RuntimeError("无法通过浏览器协议检查草稿保存控件") from exc

        def descendants(node: Dict[str, Any]):
            yield node
            for key in ("children", "shadowRoots", "contentDocument"):
                values = node.get(key) or []
                if isinstance(values, dict):
                    values = [values]
                for child in values:
                    if isinstance(child, dict):
                        yield from descendants(child)

        hosts = [
            node
            for node in descendants(tree)
            if str(node.get("nodeName", "")).lower() == "xhs-publish-btn"
        ]
        if len(hosts) != 1:
            raise RuntimeError("新版发布控件不唯一，拒绝猜测草稿保存入口")

        def text_content(node: Dict[str, Any]) -> str:
            node_value = node.get("nodeValue")
            if isinstance(node_value, str) and node_value:
                return node_value
            return "".join(
                text_content(child)
                for child in node.get("children", []) or []
                if isinstance(child, dict)
            )

        buttons = []
        for node in descendants(hosts[0]):
            if str(node.get("nodeName", "")).lower() != "button":
                continue
            label = " ".join(text_content(node).split())
            if label in DRAFT_SAVE_LABELS:
                buttons.append((node, label))
        if len(buttons) != 1:
            raise RuntimeError("未找到唯一语义明确的草稿保存按钮")

        node, label = buttons[0]
        node_id = node.get("nodeId")
        if not node_id:
            raise RuntimeError("草稿保存按钮缺少可解析的浏览器节点")
        try:
            resolved = cdp.send("DOM.resolveNode", {"nodeId": node_id})
            object_id = resolved.get("object", {}).get("objectId")
            if not object_id:
                raise RuntimeError("无法解析草稿保存按钮")
            result = cdp.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": object_id,
                    "functionDeclaration": """
                        function(expectedLabel) {
                            const actualLabel = (this.textContent || '').trim().replace(/\\s+/g, ' ');
                            const style = getComputedStyle(this);
                            const rect = this.getBoundingClientRect();
                            const visible = Boolean(
                                this.isConnected &&
                                rect.width > 0 &&
                                rect.height > 0 &&
                                style.display !== 'none' &&
                                style.visibility !== 'hidden' &&
                                style.opacity !== '0'
                            );
                            if (actualLabel !== expectedLabel) {
                                return {ok: false, reason: 'label_changed'};
                            }
                            if (!visible) {
                                return {ok: false, reason: 'not_visible'};
                            }
                            if (this.disabled || this.hasAttribute('disabled') || this.getAttribute('aria-disabled') === 'true') {
                                return {ok: false, reason: 'disabled'};
                            }
                            this.click();
                            return {ok: true, label: actualLabel};
                        }
                    """,
                    "arguments": [{"value": label}],
                    "returnByValue": True,
                },
            )
            value = result.get("result", {}).get("value")
            if not isinstance(value, dict) or value.get("ok") is not True:
                reason = value.get("reason", "unknown") if isinstance(value, dict) else "unknown"
                raise RuntimeError(f"草稿保存按钮复核失败: {reason}")
            return {"save_control": label, "save_control_clicked": True}
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("点击语义明确的草稿保存按钮失败") from exc
        finally:
            try:
                if "object_id" in locals() and object_id:
                    cdp.send("Runtime.releaseObject", {"objectId": object_id})
            except Exception:
                pass

    def _save_draft(
        self,
        title: str,
        *,
        expected_body: Optional[str] = None,
        require_cover: bool = False,
        timeout: float = 15,
    ) -> Dict[str, Any]:
        """Save through the widget, reopen the card, and verify its contents."""
        page = self.client.page
        if expected_body is None:
            raise ValueError("保存草稿必须提供预期正文以完成读回校验")
        save_control = self._click_shadow_save_control()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            draft_box = page.locator(DRAFT_BOX_SELECTOR)
            title_matches = page.get_by_text(title, exact=True)
            if self._is_visible(draft_box):
                visible_title_nodes = [
                    title_matches.nth(index)
                    for index in range(title_matches.count())
                    if title_matches.nth(index).is_visible()
                ]
                visible_titles = len(visible_title_nodes)
                if visible_titles == 1:
                    try:
                        card = visible_title_nodes[0].locator(
                            "xpath=ancestor::*[.//*[normalize-space(text())='编辑']][1]"
                        )
                        edit = card.get_by_text("编辑", exact=True)
                        if edit.count() != 1 or not self._is_visible(edit):
                            raise ValueError(f"保存后草稿编辑入口不唯一: {title}")
                        edit.click()
                        time.sleep(0.5)
                        title_input = page.locator('div.d-input input').first
                        if title_input.input_value() != title:
                            raise ValueError("保存后草稿标题读回不一致")
                        body = self._read_content()
                        body_ok = expected_body is None or (
                            self._normalize_editor_text(body)
                            == self._normalize_editor_text(expected_body)
                        )
                        if not body_ok:
                            raise ValueError("保存后草稿正文读回不一致")
                        cover = self._cover_readback()
                        if require_cover and not cover["cover_ok"]:
                            raise ValueError("保存后草稿封面读回不一致")
                        return {
                            "draft_box_visible": True,
                            "draft_title": title,
                            "draft_title_exact": True,
                            "body_ok": body_ok,
                            "cover_readback": cover,
                            "draft_readback": "title_body_cover",
                            **save_control,
                        }
                    except ValueError:
                        raise
                    except Exception as exc:
                        raise RuntimeError("无法重新打开保存后的精确草稿卡片") from exc
                if visible_titles > 1:
                    raise ValueError(f"保存后草稿标题不唯一: {title}")
            time.sleep(0.2)
        raise TimeoutError(f"保存草稿后未读回精确标题: {title}")

    def _video_preview_status(self) -> Dict[str, Any]:
        """Keep local blob playback evidence separate from remote playback."""
        try:
            state = self.client.page.evaluate(
                """() => {
                    const media = Array.from(document.querySelectorAll('video'));
                    const item = media.find(node => node.offsetParent !== null);
                    if (!item) return {status: 'unavailable', source: 'unknown'};
                    const src = item.currentSrc || item.src || '';
                    const source = /^(blob:|data:|file:)/.test(src) ? 'local'
                        : /^https?:/.test(src) ? 'remote' : 'unknown';
                    const evidence = {source, ready_state: item.readyState};
                    if (item.error) return {...evidence, status: 'error', code: item.error.code};
                    if (item.readyState >= 2 && Number.isFinite(item.duration) && item.duration > 0 && src) {
                        return {...evidence, status: 'available', duration: item.duration};
                    }
                    return {...evidence, status: 'pending'};
                }"""
            )
        except Exception:
            state = {"status": "unavailable", "source": "unknown"}
        if not isinstance(state, dict):
            state = {"status": "unavailable", "source": "unknown"}
        source, status = state.get("source", "unknown"), state.get("status", "unavailable")
        return {
            "preview_source": source,
            "local_preview": status if source == "local" else "not_observed",
            "remote_preview": status if source == "remote" else "not_observed",
            "media_error_code": state.get("code"),
        }

    def _click_publish_button(self) -> bool:
        """点击发布按钮

        Go 参考: publish.go:401-463 findPublishButton + publish.go:465-508 clickPublishWidget
        优先检测新版 xhs-publish-btn Web Component，回退到旧版 button.bg-red。
        新版 widget 通过 bounding_box 坐标 + mouse.click 点击。
        """
        page = self.client.page

        # 1. 优先检测新版 xhs-publish-btn Web Component
        try:
            widgets = page.locator("xhs-publish-btn")
            for i in range(widgets.count()):
                widget = widgets.nth(i)

                # 检查 is-publish 属性
                is_publish = widget.get_attribute("is-publish")
                if is_publish == "false":
                    continue

                # 检查 submit-disabled 属性
                submit_disabled = widget.get_attribute("submit-disabled")
                if submit_disabled == "true":
                    print("新版发布按钮不可点击 (submit-disabled=true)", file=sys.stderr)
                    time.sleep(1)
                    continue

                # 通过坐标点击 widget
                widget.scroll_into_view_if_needed()
                time.sleep(0.2)

                box = widget.bounding_box()
                if box:
                    # 点击位置: x 在 65% 宽处, y 在中间
                    x = box['x'] + box['width'] * 0.65
                    y = box['y'] + box['height'] / 2
                    page.mouse.click(x, y)
                    time.sleep(3)
                    print("已点击新版发布按钮 (xhs-publish-btn)", file=sys.stderr)
                    return True
                else:
                    print("新版发布按钮无 bounding box", file=sys.stderr)

            # 如果找到了新版 widget 但都无法点击，视为已处理
            if widgets.count() > 0:
                print("所有新版发布按钮均不可用", file=sys.stderr)
                return False
        except Exception as e:
            print(f"检测新版发布按钮出错: {e}", file=sys.stderr)

        # 2. 回退到旧版 button.bg-red
        try:
            btn = page.locator('.publish-page-publish-btn button.bg-red')
            if btn.count() > 0:
                btn.first.click()
                time.sleep(3)
                print("已点击发布按钮 (旧版)", file=sys.stderr)
                return True
            else:
                print("未找到发布按钮", file=sys.stderr)
                return False
        except Exception as e:
            print(f"点击发布按钮失败: {e}", file=sys.stderr)
            return False

    @staticmethod
    def _safe_page_url(page) -> str:
        """Read the current page URL without trusting mock or browser errors."""
        try:
            current_url = page.url
            return current_url if isinstance(current_url, str) else ""
        except Exception:
            return ""

    @staticmethod
    def _url_location(url: str) -> tuple[str, str]:
        """Return a query-independent URL location for transition checks."""
        try:
            parsed = urlsplit(url)
            return parsed.netloc.lower(), parsed.path.rstrip("/").lower()
        except ValueError:
            return "", ""

    @staticmethod
    def _is_publish_workflow_url(url: str) -> bool:
        """Return whether a URL still belongs to the creator publish flow."""
        host, path = PublishAction._url_location(url)
        return host == "creator.xiaohongshu.com" and "/publish" in path

    @staticmethod
    def _redirect_failure_signal(url: str) -> Optional[str]:
        """Classify login and security-verification redirects."""
        lowered = url.lower()
        if any(pattern.lower() in lowered for pattern in CAPTCHA_URL_PATTERNS):
            return "captcha_redirect"
        if any(marker in lowered for marker in LOGIN_URL_MARKERS):
            return "login_redirect"
        return None

    def _publish_success_feedback_count(self) -> int:
        """Count visible success feedback nodes for pre/post-click comparison."""
        try:
            feedback = self.client.page.get_by_text("发布成功", exact=False)
            return sum(
                1
                for index in range(feedback.count())
                if feedback.nth(index).is_visible()
            )
        except Exception:
            return 0

    def _has_security_challenge(self) -> bool:
        """Reuse the client URL/title checks without accepting mock truthiness."""
        try:
            return self.client._check_captcha() is True
        except Exception:
            return False

    @staticmethod
    def _is_trusted_post_publish_url(url: str) -> bool:
        """Accept only known creator-host destinations as a URL success signal."""
        host, path = PublishAction._url_location(url)
        if host not in TRUSTED_CONFIRMATION_HOSTS:
            return False
        if any(marker in path for marker in FAILED_DESTINATION_MARKERS):
            return False
        return "/publish" not in path

    def _wait_for_publish_confirmation(
        self,
        *,
        initial_url: Optional[str] = None,
        initial_success_feedback_count: int = 0,
        timeout: float = 15.0,
        poll_interval: float = 0.5,
        monotonic=None,
        sleep=None,
    ) -> PublishConfirmation:
        """Observe post-click signals and never infer success from the click alone."""
        monotonic = monotonic or time.monotonic
        sleep = sleep or time.sleep
        deadline = monotonic() + timeout
        initial_url = initial_url or self._safe_page_url(self.client.page)
        initial_location = self._url_location(initial_url)
        initial_was_publish = self._is_publish_workflow_url(initial_url)
        last_url = initial_url

        while monotonic() < deadline:
            current_url = self._safe_page_url(self.client.page)
            if current_url:
                last_url = current_url
                failure_signal = self._redirect_failure_signal(current_url)
                if failure_signal:
                    message = (
                        "发布后进入安全验证页面"
                        if failure_signal == "captcha_redirect"
                        else "发布后进入登录页面"
                    )
                    return PublishConfirmation(
                        status=PUBLISH_STATUS_FAILED,
                        message=message,
                        signal=failure_signal,
                        url=current_url,
                    )

            if self._has_security_challenge():
                return PublishConfirmation(
                    status=PUBLISH_STATUS_FAILED,
                    message="发布后进入安全验证页面",
                    signal="captcha_detected",
                    url=current_url,
                )

            if self._publish_success_feedback_count() > initial_success_feedback_count:
                return PublishConfirmation(
                    status=PUBLISH_STATUS_CONFIRMED,
                    message="已观察到发布成功提示",
                    signal="success_feedback",
                    url=current_url,
                )

            current_location = self._url_location(current_url)
            if (
                initial_was_publish
                and current_location != initial_location
                and self._is_trusted_post_publish_url(current_url)
            ):
                return PublishConfirmation(
                    status=PUBLISH_STATUS_CONFIRMED,
                    message="发布后已离开发布页面",
                    signal="url_left_publish_flow",
                    url=current_url,
                )

            sleep(poll_interval)

        return PublishConfirmation(
            status=PUBLISH_STATUS_SUBMITTED_UNCONFIRMED,
            message="已点击发布，但未观察到成功信号，请人工复核",
            signal="confirmation_timeout",
            url=last_url,
        )

    def _publish_and_confirm(
        self,
        *,
        timeout: float = 15.0,
        poll_interval: float = 0.5,
        monotonic=None,
        sleep=None,
    ) -> PublishConfirmation:
        """Click publish and return a trustworthy confirmation state."""
        initial_url = self._safe_page_url(self.client.page)
        initial_success_feedback_count = self._publish_success_feedback_count()
        if not self._click_publish_button():
            return PublishConfirmation(
                status=PUBLISH_STATUS_FAILED,
                message="未能点击发布按钮",
                signal="click_failed",
                url=self._safe_page_url(self.client.page),
            )
        return self._wait_for_publish_confirmation(
            initial_url=initial_url,
            initial_success_feedback_count=initial_success_feedback_count,
            timeout=timeout,
            poll_interval=poll_interval,
            monotonic=monotonic,
            sleep=sleep,
        )

    @staticmethod
    def _confirmation_fields(confirmation: PublishConfirmation) -> Dict[str, Any]:
        """Expose stable compatibility fields for CLI and Python callers."""
        return {
            "status": confirmation.status,
            "success": confirmation.success,
            "published": confirmation.success,
            "message": confirmation.message,
            "confirmation_signal": confirmation.signal,
            "confirmation_url": confirmation.url,
        }

    @staticmethod
    def _emit_validation_warnings(validation: PublishValidation) -> None:
        for warning in validation.warnings:
            print(f"警告: {warning}", file=sys.stderr)

    def _check_publish_ready(
        self,
        *,
        expected_title: Optional[str] = None,
        expected_content: Optional[str] = None,
        expected_account: Optional[str] = None,
        expected_visibility: str = "公开可见",
        require_cover: bool = False,
    ) -> Dict[str, Any]:
        """Check title/body/cover/visibility/account and upload readiness."""
        page = self.client.page
        status = {}

        # 检查标题
        try:
            title_input = page.locator('div.d-input input')
            status["title"] = title_input.input_value() if title_input.count() > 0 else ""
        except Exception:
            status["title"] = ""
        status["title_ok"] = bool(status["title"])

        try:
            btn = page.locator('.publish-page-publish-btn button.bg-red')
            status["publish_button_visible"] = btn.count() > 0 and btn.is_visible()
        except Exception:
            status["publish_button_visible"] = False

        # Read the body through the unique contenteditable binding after the
        # legacy checks above, preserving the established mock/browser order.
        status["content"] = self._read_content()
        status["content_ok"] = (
            self._normalize_editor_text(status["content"])
            == self._normalize_editor_text(expected_content)
            if expected_content is not None
            else bool(status["content"])
        )
        if expected_title is not None:
            status["title_ok"] = status["title"] == expected_title

        # The closed-shadow widget is the current publish control.  A legacy
        # button remains a compatibility fallback for older Creator Center UI.
        status["publish_widget_visible"] = False
        status["publish_widget_ready"] = False
        try:
            widgets = page.locator("xhs-publish-btn")
            for index in range(widgets.count()):
                widget = widgets.nth(index)
                if not self._is_visible(widget):
                    continue
                status["publish_widget_visible"] = True
                disabled = widget.get_attribute("submit-disabled")
                is_publish = widget.get_attribute("is-publish")
                if disabled != "true" and is_publish != "false":
                    status["publish_widget_ready"] = widget.bounding_box() is not None
                    if status["publish_widget_ready"]:
                        break
        except Exception:
            pass

        status["publish_button_ready"] = bool(
            status["publish_widget_ready"] or status["publish_button_visible"]
        )
        cover = self._cover_readback()
        status["cover_readback"] = cover
        status["cover_ok"] = cover["cover_ok"] if require_cover else True
        status["visibility_ok"] = False
        try:
            permission = page.locator("div.permission-card-wrapper")
            if permission.count() == 1 and permission.first.is_visible() is True:
                selected = permission.first.locator("div.d-select-content")
                selected = selected.first if selected.count() else permission.first
                if not selected.is_visible():
                    raise RuntimeError("可见范围当前选中项不可见")
                selected_text = selected.inner_text() or ""
                status["visibility_ok"] = expected_visibility in selected_text
        except Exception:
            status["visibility_ok"] = False
        if expected_account:
            status.update(self._check_account_binding(expected_account))
        else:
            status["account_ok"] = True
        status["expected_account"] = expected_account
        status["ready"] = all(
            (
                status["title_ok"],
                status["content_ok"],
                status["cover_ok"],
                status["visibility_ok"],
                status["account_ok"],
                status["publish_button_ready"],
            )
        )
        return status

    def publish_image(
        self,
        title: str,
        content: str,
        image_paths: List[str],
        tags: Optional[List[str]] = None,
        schedule_time: Optional[str] = None,
        auto_publish: bool = False,
        is_original: bool = False,
        visibility: str = "公开可见",
    ) -> Dict[str, Any]:
        """
        发布图文笔记

        Args:
            title: 标题（建议 <=20 字）
            content: 正文
            image_paths: 图片文件路径列表
            tags: 话题标签列表
            schedule_time: 定时发布时间（格式 2025-01-01 12:00），None 为立即
            auto_publish: 是否自动点击发布（默认 False，停在发布按钮处）
            is_original: 是否声明原创（默认 False）
            visibility: 可见范围，公开可见/仅自己可见/仅互关好友可见

        Returns:
            操作结果
        """
        validation = validate_publish_request(
            title=title,
            media_paths=image_paths,
            schedule_time=schedule_time,
        )
        self._emit_validation_warnings(validation)
        validated_image_paths = list(validation.media_paths or tuple(image_paths))

        self._navigate_to_publish()
        self._click_publish_tab("上传图文")

        # 1. 上传图片
        self._upload_images(validated_image_paths)
        time.sleep(random.uniform(1.5, 3.0))

        # 2. 填写标题
        self._fill_title(title)
        time.sleep(random.uniform(1.0, 2.0))

        # 3. 填写正文
        self._fill_content(content)
        time.sleep(random.uniform(1.0, 2.5))

        # 4. 添加标签
        if tags:
            self._input_tags(tags)
            time.sleep(random.uniform(1.0, 2.0))

        # 5. 设置可见范围
        self._set_visibility(self.client.page, visibility)
        time.sleep(random.uniform(0.5, 1.0))

        # 6. 原创声明
        if is_original:
            self._set_original(self.client.page)
            time.sleep(random.uniform(0.5, 1.0))

        # 7. 定时发布
        if schedule_time:
            self._set_schedule(schedule_time)
            time.sleep(random.uniform(0.5, 1.5))

        # 8. 校验三要素
        ready = self._check_publish_ready()
        print(f"发布前校验: {ready}", file=sys.stderr)

        # 9. 是否自动发布
        if auto_publish:
            confirmation = self._publish_and_confirm()
            result = {
                "action": "publish_image",
                "title": title,
                "image_count": len(validated_image_paths),
                "tags": tags or [],
                "schedule_time": schedule_time,
                "is_original": is_original,
                "visibility": visibility,
                "warnings": list(validation.warnings),
            }
            result.update(self._confirmation_fields(confirmation))
            return result
        else:
            return {
                "status": "ready",
                "action": "publish_image",
                "title": title,
                "image_count": len(validated_image_paths),
                "tags": tags or [],
                "schedule_time": schedule_time,
                "is_original": is_original,
                "visibility": visibility,
                "success": False,
                "published": False,
                "ready_check": ready,
                "warnings": list(validation.warnings),
                "message": "已填写完毕，停在发布按钮处。请确认后使用 --auto-publish 发布。",
            }

    def publish_video(
        self,
        title: str,
        content: str,
        video_path: str,
        tags: Optional[List[str]] = None,
        schedule_time: Optional[str] = None,
        auto_publish: bool = False,
        is_original: bool = False,
        visibility: str = "公开可见",
        cover_path: Optional[str] = None,
        resume_draft: bool = False,
        save_draft: bool = True,
        upload_timeout: float = 600,
        expected_account: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发布视频笔记

        Args:
            title: 标题
            content: 正文
            video_path: 视频文件路径
            tags: 话题标签
            schedule_time: 定时发布时间
            auto_publish: 是否自动发布（默认 False）
            is_original: 是否声明原创（默认 False）
            visibility: 可见范围，公开可见/仅自己可见/仅互关好友可见
            cover_path: 可选的本地视频封面图片
            resume_draft: 按完全匹配标题恢复现有草稿，不重新上传视频
            save_draft: 准备模式下保存草稿并读回精确标题
            upload_timeout: 视频处理最长等待秒数
            expected_account: 可选的当前账号精确显示名

        Returns:
            操作结果
        """
        validation = validate_publish_request(
            title=title,
            media_paths=None if resume_draft else [video_path],
            schedule_time=schedule_time,
        )
        self._emit_validation_warnings(validation)
        validated_video_path = (validation.media_paths or (video_path,))[0]
        validated_cover_path = None
        if cover_path:
            validated_cover_path = validate_media_paths([cover_path])[0]
        expected_body = self._compose_expected_body(content, tags)

        self._navigate_to_publish()
        account_readback = self._check_account_binding(expected_account)
        if not account_readback["account_ok"]:
            return {
                "status": PUBLISH_STATUS_FAILED,
                "action": "publish_video",
                "title": title,
                "video_path": video_path,
                "success": False,
                "published": False,
                "account_readback": account_readback,
                "message": "当前账号与 expected_account 不匹配，未上传或编辑",
                "warnings": list(validation.warnings),
            }
        if resume_draft:
            try:
                draft_readback = self._resume_draft(
                    title,
                    expected_body=expected_body,
                    require_cover=True,
                )
            except (RuntimeError, ValueError, TimeoutError) as exc:
                return {
                    "status": PUBLISH_STATUS_FAILED,
                    "action": "publish_video",
                    "title": title,
                    "video_path": video_path,
                    "resume_draft": True,
                    "success": False,
                    "published": False,
                    "message": str(exc),
                    "warnings": list(validation.warnings),
                }
        else:
            self._click_publish_tab("上传视频")
            self._upload_video(validated_video_path, timeout=upload_timeout)
            self._fill_title(title)
            self._fill_content(content)
            draft_readback = {"resume_draft": False}

        # Cover parsing is independent from video upload.  If the editor gets
        # stuck, return a hard failure and never retry the video upload.
        cover_readback = {"cover_ok": True}
        if validated_cover_path and not resume_draft:
            try:
                cover_readback = self._set_cover(validated_cover_path)
            except (RuntimeError, ValueError, TimeoutError) as exc:
                return {
                    "status": PUBLISH_STATUS_FAILED,
                    "action": "publish_video",
                    "title": title,
                    "video_path": video_path,
                    "cover_path": cover_path,
                    "success": False,
                    "published": False,
                    "message": str(exc),
                    "warnings": list(validation.warnings),
                }

        # Tags are appended as exact text and never selected from a fuzzy
        # suggestion list.  A resumed draft keeps its existing body intact.
        if tags and not resume_draft:
            try:
                self._input_tags(tags)
            except (RuntimeError, ValueError) as exc:
                return {
                    "status": PUBLISH_STATUS_FAILED,
                    "action": "publish_video",
                    "title": title,
                    "video_path": video_path,
                    "cover_path": cover_path,
                    "success": False,
                    "published": False,
                    "message": str(exc),
                    "warnings": list(validation.warnings),
                }

        # 5. 设置可见范围
        self._set_visibility(self.client.page, visibility)

        # 6. 原创声明
        if is_original:
            self._set_original(self.client.page)

        # 7. 定时发布
        if schedule_time:
            self._set_schedule(schedule_time)

        # 8. 校验所有 fields required for a publish click.
        ready = self._check_publish_ready(
            expected_title=title,
            expected_content=expected_body,
            expected_account=expected_account,
            expected_visibility=visibility,
            require_cover=True,
        )
        ready["video_preview"] = self._video_preview_status()
        ready["cover_readback"] = cover_readback
        ready["draft_readback"] = draft_readback
        ready["account_readback"] = account_readback
        print(f"发布前校验: {ready}", file=sys.stderr)

        base = {
            "action": "publish_video",
            "title": title,
            "video_path": video_path,
            "cover_path": cover_path,
            "schedule_time": schedule_time,
            "is_original": is_original,
            "visibility": visibility,
            "resume_draft": resume_draft,
            "warnings": list(validation.warnings),
            "ready_check": ready,
        }

        # A missing readiness key is a hard failure.  Test doubles must model
        # the same evidence as the real browser path.
        required_ready = (
            "title_ok",
            "content_ok",
            "cover_ok",
            "visibility_ok",
            "account_ok",
            "publish_button_ready",
        )
        if not all(ready.get(key, False) for key in required_ready):
            return {
                **base,
                "status": PUBLISH_STATUS_FAILED,
                "success": False,
                "published": False,
                "message": "发布前校验未通过，未点击发布按钮",
            }

        if auto_publish:
            confirmation = self._publish_and_confirm()
            result = dict(base)
            result.update(self._confirmation_fields(confirmation))
            return result

        if not save_draft:
            return {
                **base,
                "status": "ready",
                "success": False,
                "published": False,
                "message": "已填写完毕，未保存草稿。",
            }

        try:
            draft_saved = self._save_draft(
                title,
                expected_body=expected_body,
                require_cover=True,
            )
        except (RuntimeError, ValueError, TimeoutError) as exc:
            return {
                **base,
                "status": PUBLISH_STATUS_FAILED,
                "success": False,
                "published": False,
                "message": str(exc),
            }
        return {
            **base,
            "status": PUBLISH_STATUS_DRAFT_SAVED,
            "success": False,
            "published": False,
            "draft_saved": True,
            "draft_readback": draft_saved,
            "message": "已保存草稿并读回完全匹配的标题，未点击发布。",
        }


    def publish_longform(
        self,
        title: str,
        content: str,
        auto_publish: bool = False,
    ) -> Dict[str, Any]:
        """
        发布长文笔记（通过创作者中心"写长文"功能）

        流程：导航到创作者中心 → 点击「写长文」→「新的创作」→ 输入标题正文
              → 一键排版 → 选择模板 → 下一步 → （可选）发布

        Args:
            title: 标题
            content: 正文内容
            auto_publish: 是否自动发布（默认 False，停在发布页）

        Returns:
            操作结果
        """
        validation = validate_publish_request(title=title)
        self._emit_validation_warnings(validation)
        page = self.client.page

        # 1. 导航到创作者中心发布页
        self._navigate_to_publish()
        time.sleep(random.uniform(1.0, 2.0))

        # 2. 点击侧边栏「写长文」
        try:
            longform_btn = page.get_by_text("写长文", exact=True)
            if longform_btn.count() > 0:
                longform_btn.first.click()
            else:
                # 回退：用选择器查找
                page.locator('div.creator-tab:has-text("写长文")').click()
            time.sleep(random.uniform(1.5, 3.0))
            print("已点击「写长文」", file=sys.stderr)
        except Exception as e:
            print(f"点击「写长文」失败: {e}", file=sys.stderr)
            return {"status": "error", "action": "publish_longform", "message": f"点击写长文失败: {e}"}

        # 3. 点击「新的创作」
        try:
            new_btn = page.get_by_text("新的创作", exact=False)
            if new_btn.count() > 0:
                new_btn.first.click()
                time.sleep(random.uniform(2.0, 3.5))
                print("已点击「新的创作」", file=sys.stderr)
        except Exception as e:
            print(f"点击「新的创作」失败（可能已在编辑页）: {e}", file=sys.stderr)

        # 4. 输入标题
        try:
            title_input = page.locator('input[placeholder*="标题"], div.title-input input, div.d-input input')
            if title_input.count() > 0:
                title_input.first.fill(title)
                time.sleep(random.uniform(0.5, 1.5))
                print(f"长文标题已填写: {title}", file=sys.stderr)
            else:
                print("未找到长文标题输入框", file=sys.stderr)
        except Exception as e:
            print(f"填写长文标题失败: {e}", file=sys.stderr)

        # 5. 输入正文
        time.sleep(random.uniform(0.5, 1.0))
        try:
            # 长文编辑器可能是 Quill 或 contenteditable
            editor = None
            for selector in ['div.ql-editor', '[role="textbox"]', 'div[contenteditable="true"]']:
                loc = page.locator(selector)
                if loc.count() > 0:
                    editor = loc.first
                    break

            if editor:
                editor.click()
                time.sleep(random.uniform(0.3, 0.8))
                page.keyboard.type(content, delay=random.randint(15, 40))
                time.sleep(random.uniform(0.5, 1.5))
                print("长文正文已填写", file=sys.stderr)
            else:
                print("未找到长文正文编辑器", file=sys.stderr)
        except Exception as e:
            print(f"填写长文正文失败: {e}", file=sys.stderr)

        # 6. 点击「一键排版」
        time.sleep(random.uniform(1.0, 2.0))
        try:
            format_btn = page.get_by_text("一键排版", exact=False)
            if format_btn.count() > 0:
                format_btn.first.click()
                time.sleep(random.uniform(2.0, 3.5))
                print("已点击「一键排版」", file=sys.stderr)
            else:
                print("未找到「一键排版」按钮，跳过", file=sys.stderr)
        except Exception as e:
            print(f"点击一键排版失败: {e}", file=sys.stderr)

        # 7. 选择模板（第一个「简约基础」）
        try:
            template_items = page.locator('.template-item, .style-item')
            if template_items.count() > 0:
                template_items.first.click()
                time.sleep(random.uniform(1.0, 2.0))
                print("已选择排版模板", file=sys.stderr)
        except Exception as e:
            print(f"选择模板失败: {e}", file=sys.stderr)

        # 8. 点击「下一步」
        try:
            next_btn = page.get_by_text("下一步", exact=True)
            if next_btn.count() > 0:
                next_btn.first.click()
                time.sleep(random.uniform(2.0, 3.5))
                print("已点击「下一步」", file=sys.stderr)
        except Exception as e:
            print(f"点击下一步失败: {e}", file=sys.stderr)

        # 9. 是否自动发布
        if auto_publish:
            confirmation = self._publish_and_confirm()
            result = {
                "action": "publish_longform",
                "title": title,
                "warnings": list(validation.warnings),
            }
            result.update(self._confirmation_fields(confirmation))
            return result
        else:
            return {
                "status": "ready",
                "action": "publish_longform",
                "title": title,
                "success": False,
                "published": False,
                "warnings": list(validation.warnings),
                "message": "长文已填写完毕，停在发布页。请确认后使用 --auto-publish 发布。",
            }


def md_to_images(
    markdown_text: str,
    output_dir: str = ".",
    width: int = 1080,
    css: str = "",
) -> List[str]:
    """
    将 Markdown 文本渲染为长文图片（利用 Playwright 截图）

    Args:
        markdown_text: Markdown 文本
        output_dir: 输出目录
        width: 图片宽度（像素）
        css: 自定义 CSS 样式

    Returns:
        生成的图片路径列表
    """
    try:
        import markdown
    except ImportError:
        print("需要安装 markdown 库: pip install markdown", file=sys.stderr)
        raise

    # 将 Markdown 转为 HTML
    html_content = markdown.markdown(
        markdown_text,
        extensions=['tables', 'fenced_code', 'codehilite', 'nl2br'],
    )

    default_css = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                     "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        padding: 40px 50px;
        line-height: 1.8;
        color: #333;
        background: #fff;
        max-width: 100%;
        margin: 0 auto;
        font-size: 16px;
    }
    h1 { font-size: 24px; font-weight: bold; margin: 20px 0 10px; color: #222; }
    h2 { font-size: 20px; font-weight: bold; margin: 18px 0 8px; color: #333; }
    h3 { font-size: 18px; font-weight: bold; margin: 15px 0 6px; color: #444; }
    p { margin: 8px 0; }
    ul, ol { padding-left: 20px; }
    li { margin: 4px 0; }
    blockquote {
        border-left: 4px solid #ff2442;
        padding: 8px 16px;
        margin: 12px 0;
        background: #fff5f5;
        color: #555;
    }
    code {
        background: #f5f5f5;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 14px;
    }
    pre {
        background: #f5f5f5;
        padding: 16px;
        border-radius: 6px;
        overflow-x: auto;
    }
    img { max-width: 100%; border-radius: 8px; }
    hr { border: none; border-top: 1px solid #eee; margin: 20px 0; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; }
    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
    th { background: #f5f5f5; }
    """

    full_css = default_css + "\n" + css
    full_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width={width}">
<style>{full_css}</style>
</head><body>{html_content}</body></html>"""

    os.makedirs(output_dir, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.set_content(full_html)
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        # 获取实际内容高度
        total_height = page.evaluate("document.body.scrollHeight")

        # 如果内容不太长（<=4000px），直接截一张
        # 否则分页截图（每张最多 3000px）
        image_paths = []
        max_page_height = 3000

        if total_height <= max_page_height + 500:
            # 单张截图
            page.set_viewport_size({"width": width, "height": total_height + 40})
            time.sleep(0.3)
            img_path = os.path.join(output_dir, "md_page_1.png")
            page.screenshot(path=img_path, full_page=True)
            image_paths.append(img_path)
        else:
            # 分页截图
            page_num = 1
            y_offset = 0
            while y_offset < total_height:
                chunk_height = min(max_page_height, total_height - y_offset)
                img_path = os.path.join(output_dir, f"md_page_{page_num}.png")
                page.screenshot(
                    path=img_path,
                    clip={"x": 0, "y": y_offset, "width": width, "height": chunk_height},
                )
                image_paths.append(img_path)
                y_offset += chunk_height
                page_num += 1

        browser.close()

    print(f"Markdown 已渲染为 {len(image_paths)} 张图片", file=sys.stderr)
    return image_paths


# ============================================================
# 便捷函数
# ============================================================

def publish_image(
    title: str,
    content: str,
    image_paths: List[str],
    tags: Optional[List[str]] = None,
    schedule_time: Optional[str] = None,
    auto_publish: bool = False,
    is_original: bool = False,
    visibility: str = "公开可见",
    headless: bool = True,
    cookie_path: str = DEFAULT_COOKIE_PATH,
) -> Dict[str, Any]:
    """发布图文笔记"""
    client = XiaohongshuClient(headless=headless, cookie_path=cookie_path)
    try:
        client.start()
        action = PublishAction(client)
        return action.publish_image(
            title=title, content=content, image_paths=image_paths,
            tags=tags, schedule_time=schedule_time, auto_publish=auto_publish,
            is_original=is_original, visibility=visibility,
        )
    finally:
        client.close()


def publish_video(
    title: str,
    content: str,
    video_path: str,
    tags: Optional[List[str]] = None,
    schedule_time: Optional[str] = None,
    auto_publish: bool = False,
    is_original: bool = False,
    visibility: str = "公开可见",
    headless: bool = True,
    cookie_path: str = DEFAULT_COOKIE_PATH,
    cover_path: Optional[str] = None,
    resume_draft: bool = False,
    save_draft: bool = True,
    upload_timeout: float = 600,
    expected_account: Optional[str] = None,
) -> Dict[str, Any]:
    """发布视频笔记"""
    client = XiaohongshuClient(headless=headless, cookie_path=cookie_path)
    try:
        client.start()
        action = PublishAction(client)
        return action.publish_video(
            title=title, content=content, video_path=video_path,
            tags=tags, schedule_time=schedule_time, auto_publish=auto_publish,
            is_original=is_original, visibility=visibility,
            cover_path=cover_path, resume_draft=resume_draft,
            save_draft=save_draft, upload_timeout=upload_timeout,
            expected_account=expected_account,
        )
    finally:
        client.close()


def publish_longform(
    title: str,
    content: str,
    auto_publish: bool = False,
    headless: bool = True,
    cookie_path: str = DEFAULT_COOKIE_PATH,
) -> Dict[str, Any]:
    """发布长文笔记"""
    client = XiaohongshuClient(headless=headless, cookie_path=cookie_path)
    try:
        client.start()
        action = PublishAction(client)
        return action.publish_longform(
            title=title, content=content, auto_publish=auto_publish,
        )
    finally:
        client.close()


def publish_markdown(
    title: str,
    markdown_text: str,
    extra_content: str = "",
    tags: Optional[List[str]] = None,
    schedule_time: Optional[str] = None,
    auto_publish: bool = False,
    image_width: int = 1080,
    output_dir: str = "",
    headless: bool = True,
    cookie_path: str = DEFAULT_COOKIE_PATH,
) -> Dict[str, Any]:
    """
    将 Markdown 渲染为图片后发布图文笔记

    Args:
        title: 标题
        markdown_text: Markdown 内容
        extra_content: 正文区的额外文字说明
        tags: 话题标签
        schedule_time: 定时发布
        auto_publish: 是否自动发布
        image_width: 图片宽度
        output_dir: 图片输出目录（默认临时目录）
        headless: 无头模式
        cookie_path: Cookie 路径

    Returns:
        操作结果
    """
    validation = validate_publish_request(
        title=title,
        schedule_time=schedule_time,
    )
    for warning in validation.warnings:
        print(f"警告: {warning}", file=sys.stderr)

    import tempfile
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix="xhs_md_")

    # 1. Markdown → 图片
    image_paths = md_to_images(markdown_text, output_dir=output_dir, width=image_width)

    if not image_paths:
        return {"status": "error", "message": "Markdown 渲染失败，未生成图片"}

    # 2. 发布图文
    body = extra_content or f"本文由 Markdown 渲染生成，共 {len(image_paths)} 页"
    return publish_image(
        title=title, content=body, image_paths=image_paths,
        tags=tags, schedule_time=schedule_time, auto_publish=auto_publish,
        headless=headless, cookie_path=cookie_path,
    )
