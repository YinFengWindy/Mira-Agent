import type React from "react";
import {
  getChatMessageCopyText,
  getChatMessageReplyContent,
  type MessageContextMenuState,
} from "./chatMessageActions";
import { CopyIcon, QuoteIcon } from "../shared/icons";
import { MenuItem, MenuPanel } from "../shared/ui/Menu";

type ChatMessageContextMenuProps = {
  menu: MessageContextMenuState;
  menuRef: React.RefObject<HTMLDivElement | null>;
  sending: boolean;
  onCopy: () => void;
  onQuote: () => void;
};

/** Renders the copy and quote actions for one chat message. */
export function ChatMessageContextMenu({
  menu,
  menuRef,
  sending,
  onCopy,
  onQuote,
}: ChatMessageContextMenuProps) {
  return (
    <MenuPanel
      ref={menuRef}
      data-testid="message-context-menu"
      className="fixed z-50 min-w-[132px]"
      style={{ left: menu.x, top: menu.y }}
      role="menu"
      onClick={(event) => event.stopPropagation()}
      onContextMenu={(event) => {
        event.preventDefault();
        event.stopPropagation();
      }}
    >
      <MenuItem
        data-testid="message-context-menu-copy"
        role="menuitem"
        onClick={onCopy}
        disabled={!getChatMessageCopyText(menu.message)}
      >
        <CopyIcon className="h-[14px] w-[14px] fill-current" />
        <span>复制</span>
      </MenuItem>
      <MenuItem
        data-testid="message-context-menu-quote"
        role="menuitem"
        onClick={onQuote}
        disabled={!getChatMessageReplyContent(menu.message) || sending}
      >
        <QuoteIcon className="h-[14px] w-[14px] fill-current" />
        <span>引用</span>
      </MenuItem>
    </MenuPanel>
  );
}
