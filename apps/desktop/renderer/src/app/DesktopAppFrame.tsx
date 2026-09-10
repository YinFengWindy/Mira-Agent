import type React from "react";
import { ChatImageLightbox } from "../chat/ChatImageLightbox";
import { ChatSurface } from "../chat/ChatSurface";
import type { ChatMessageNavigationScroller } from "../chat/useChatScrollController";
import { ConfirmDialog } from "../roles/ConfirmDialog";
import { RoleAssetsPage } from "../roles/RoleAssetsPage";
import { RoleCreatePage } from "../roles/RoleCreatePage";
import { RoleDetailPage } from "../roles/RoleDetailPage";
import { RoleManagementPage } from "../roles/RoleManagementPage";
import { RoleSearchDialog } from "../roles/RoleSearchDialog";
import { RoleSidebar } from "../roles/RoleSidebar";
import { RoleWorkspaceSidebar, type RoleWorkspaceSectionId } from "../roles/RoleWorkspaceSidebar";
import { usePluginUiVisibility } from "./usePluginUiVisibility";
import { SettingsPage } from "../settings/SettingsPage";
import { SettingsSidebar, type SettingsSectionId } from "../settings/SettingsSidebar";
import { cx } from "../shared/styles";
import { NavRail, pluginNavRailViewId, type NavRailViewId } from "../shell/NavRail";
import type {
  AppMainView,
  ChatSendRequest,
  NewRoleFormState,
  PendingRoleCardAction,
  RoleFormState,
  RoleRecord,
  RoleSearchResult,
  SessionPayload,
} from "../shared/types";
import type { RoleCardImportState } from "./roleCardImportState";
import { TitleBar } from "../shell/TitleBar";
import type { WorkspaceFeedback } from "./appState";

type SidebarViewState = {
  collapsed: boolean;
  width: number;
  animating: boolean;
  resizing: boolean;
  onBeginResize: (event: React.PointerEvent<HTMLDivElement>) => void;
};

type RightSidebarViewState = {
  collapsed: boolean;
  width: number;
  animating: boolean;
  resizing: boolean;
  beginResize: (event: React.PointerEvent<HTMLDivElement>) => void;
  toggle: () => void;
};

type DesktopAppFrameProps = {
  sidebarCollapsed: boolean;
  windowMaximized: boolean;
  canGoBack: boolean;
  canGoForward: boolean;
  canRefreshSession: boolean;
  onToggleSidebar: () => void;
  onGoBack: () => void;
  onGoForward: () => void;
  onRefreshSession: () => void;
  onOpenSettings: () => void;
  shellResizing: boolean;
  sidebarState: SidebarViewState;
  mainView: AppMainView;
  settingsSection: SettingsSectionId;
  onBackToChat: () => void;
  onOpenSettingsSection: (section: SettingsSectionId) => void;
  roleWorkspaceViewActive: boolean;
  roleWorkspaceSection: RoleWorkspaceSectionId;
  onOpenRoleWorkspaceSection: (section: RoleWorkspaceSectionId) => void;
  roles: RoleRecord[];
  activeRoleId: string;
  unreadCounts: Record<string, number>;
  bridgeReady: boolean;
  onOpenSearch: () => void;
  onOpenRolesWorkspace: () => void;
  onOpenStory: () => void;
  onOpenPluginPage: (pageId: string) => void;
  onOpenRole: (roleId: string) => void;
  workspaceFeedback: WorkspaceFeedback | null;
  activeRole: RoleRecord | null;
  activeSession: SessionPayload | null;
  chatLatestImagePath: string;
  chatLatestImagePosition: number;
  chatLatestImageSidebar: RightSidebarViewState;
  chatLatestImageSidebarCount: number;
  currentMood: string;
  moodIllustrationUrl: string;
  roleSelfView: string;
  relationshipTags: string[];
  lonelinessValue: number;
  conversationEndRef: React.RefObject<HTMLDivElement | null>;
  headerTitle: string;
  highlightedMessageKey: string;
  onMessageNavigationTargetMounted?: (
    messageKey: string,
    target: HTMLElement,
    scrollToMessage: ChatMessageNavigationScroller,
  ) => void;
  notice: string;
  isVisibleChatSending: boolean;
  isVisibleChatCancelling: boolean;
  visibleIllustrationUrl: string;
  windowVisible: boolean;
  onGoToNextChatImage: () => void;
  onGoToPreviousChatImage: () => void;
  onOpenChatImageLightbox: () => void;
  onOpenChatImagePreview: (target: { historyKey: string }) => void;
  onOpenRoleDetail: () => void;
  onJumpToMessage: (messageKey: string) => void;
  onBeginAttachmentDrag: (path: string) => void;
  onCopyMessage: (content: string) => void;
  onSendMessage: (request: ChatSendRequest) => Promise<boolean>;
  onCancelChat: () => void;
  onLoadOlderMessages: (sessionKey: string) => Promise<boolean>;
  detailRole: RoleRecord | null;
  pendingRoleCardAction: PendingRoleCardAction;
  onOpenRoleManagementDetail: (roleId: string) => void;
  onRequestDeleteRole: (roleId: string) => void;
  creating: boolean;
  newRoleForm: NewRoleFormState;
  onBackToRoleList: () => void;
  onCreateNewRole: () => void;
  onResetNewRoleForm: () => void;
  onUpdateNewRoleForm: React.Dispatch<React.SetStateAction<NewRoleFormState>>;
  roleCardImport: RoleCardImportState;
  onPreviewRoleCard: () => void;
  onCancelRoleCardImport: () => void;
  detailRoleId: string;
  activeIllustration: string;
  previewAvatar: string | null;
  chatBackgroundUrl: string;
  roleForm: RoleFormState;
  roleFormDirty: boolean;
  savingRole: boolean;
  onOpenAssetsPage: () => void;
  onUpdateRoleForm: React.Dispatch<React.SetStateAction<RoleFormState>>;
  onResetRoleForm: () => void;
  onSaveRole: () => void;
  savingRoleAssets: boolean;
  selectedAvatarAsset: string;
  selectedChatBackground: string;
  onBackToRoleDetail: () => void;
  onPickRoleAssets: (categoryId: string) => void;
  onUpdateRoleAssetOrganization: (categories: import("../shared/types").RoleAssetCategory[], bindings: Record<string, string>, removedIllustrations?: string[]) => Promise<boolean>;
  onRemoveRoleAsset: (path: string) => void;
  onImportRolePetPackage: () => void;
  onRemoveRolePetPackage: (packageId: string) => void;
  onSelectRolePetPackage: (packageId: string) => void;
  onSelectAvatarAsset: (path: string) => void;
  onSelectChatBackground: (path: string) => void;
  onSaveRoleAssets: (nextSelection?: { avatarAsset?: string; chatBackground?: string; moodIllustrationBindings?: Record<string, string> }) => void;
  differenceGeneration: import("../roles/roleDifferenceGeneration").RoleDifferenceGenerationState;
  onGenerateDifferences: (baseAsset: string) => void;
  showSearchDialog: boolean;
  searchQuery: string;
  searchingSessions: boolean;
  searchResults: RoleSearchResult[];
  onCloseSearchDialog: () => void;
  onSelectSearchResult: (result: RoleSearchResult) => void;
  onUpdateSearchQuery: (value: string) => void;
  pendingDeleteRole: RoleRecord | null;
  deletingRole: boolean;
  onCloseDeleteDialog: () => void;
  onConfirmDeleteRole: () => void;
  canAddToAssetLibrary: boolean;
  canGoToNextLightboxImage: boolean;
  canGoToPreviousLightboxImage: boolean;
  canLocateLightboxMessage: boolean;
  canRegenerateLightboxImage: boolean;
  addingChatImageToAssetLibrary: boolean;
  regeneratingSelectedChatImage: boolean;
  chatImageLightboxOpen: boolean;
  onAddSelectedChatImageToAssetLibrary: () => void;
  onCloseSelectedChatImageLightbox: () => void;
  onLocateSelectedChatImageMessage: () => void;
  onRegenerateSelectedChatImage: () => void;
};

/** Renders the desktop shell around the already-prepared application state. */
export function DesktopAppFrame({
  sidebarCollapsed,
  windowMaximized,
  canGoBack,
  canGoForward,
  canRefreshSession,
  onToggleSidebar,
  onGoBack,
  onGoForward,
  onRefreshSession,
  onOpenSettings,
  shellResizing,
  sidebarState,
  mainView,
  settingsSection,
  onBackToChat,
  onOpenSettingsSection,
  roleWorkspaceViewActive,
  roleWorkspaceSection,
  onOpenRoleWorkspaceSection,
  roles,
  activeRoleId,
  unreadCounts,
  bridgeReady,
  onOpenSearch,
  onOpenRolesWorkspace,
  onOpenStory,
  onOpenPluginPage,
  onOpenRole,
  workspaceFeedback,
  activeRole,
  activeSession,
  chatLatestImagePath,
  chatLatestImagePosition,
  chatLatestImageSidebar,
  chatLatestImageSidebarCount,
  currentMood,
  moodIllustrationUrl,
  roleSelfView,
  relationshipTags,
  lonelinessValue,
  conversationEndRef,
  headerTitle,
  highlightedMessageKey,
  onMessageNavigationTargetMounted,
  notice,
  isVisibleChatSending,
  isVisibleChatCancelling,
  visibleIllustrationUrl,
  windowVisible,
  onGoToNextChatImage,
  onGoToPreviousChatImage,
  onOpenChatImageLightbox,
  onOpenChatImagePreview,
  onOpenRoleDetail,
  onJumpToMessage,
  onBeginAttachmentDrag,
  onCopyMessage,
  onSendMessage,
  onCancelChat,
  onLoadOlderMessages,
  detailRole,
  pendingRoleCardAction,
  onOpenRoleManagementDetail,
  onRequestDeleteRole,
  creating,
  newRoleForm,
  onBackToRoleList,
  onCreateNewRole,
  onResetNewRoleForm,
  onUpdateNewRoleForm,
  roleCardImport,
  onPreviewRoleCard,
  onCancelRoleCardImport,
  detailRoleId,
  activeIllustration,
  previewAvatar,
  chatBackgroundUrl,
  roleForm,
  roleFormDirty,
  savingRole,
  onOpenAssetsPage,
  onUpdateRoleForm,
  onResetRoleForm,
  onSaveRole,
  savingRoleAssets,
  selectedAvatarAsset,
  selectedChatBackground,
  onBackToRoleDetail,
  onPickRoleAssets,
  onUpdateRoleAssetOrganization,
  onRemoveRoleAsset,
  onImportRolePetPackage,
  onRemoveRolePetPackage,
  onSelectRolePetPackage,
  onSelectAvatarAsset,
  onSelectChatBackground,
  onSaveRoleAssets,
  differenceGeneration,
  onGenerateDifferences,
  showSearchDialog,
  searchQuery,
  searchingSessions,
  searchResults,
  onCloseSearchDialog,
  onSelectSearchResult,
  onUpdateSearchQuery,
  pendingDeleteRole,
  deletingRole,
  onCloseDeleteDialog,
  onConfirmDeleteRole,
  canAddToAssetLibrary,
  canGoToNextLightboxImage,
  canGoToPreviousLightboxImage,
  canLocateLightboxMessage,
  canRegenerateLightboxImage,
  addingChatImageToAssetLibrary,
  regeneratingSelectedChatImage,
  chatImageLightboxOpen,
  onAddSelectedChatImageToAssetLibrary,
  onCloseSelectedChatImageLightbox,
  onLocateSelectedChatImageMessage,
  onRegenerateSelectedChatImage,
}: DesktopAppFrameProps) {
  const navRailActiveView: NavRailViewId | null = mainView.kind === "chat"
    ? "messages"
    : roleWorkspaceViewActive
      ? "roles"
      : mainView.kind === "story"
        ? "story"
        : mainView.kind === "settings"
          ? "settings"
          : mainView.kind === "plugin-page"
            ? pluginNavRailViewId(mainView.pageId)
            : null;
  const navRailUnreadTotal = Object.values(unreadCounts).reduce((total, count) => total + count, 0);
  // nav.page entries are compiled in statically (see pluginUiModules.ts); listed here
  // rather than threaded through props, matching how this frame already owns view
  // dispatch and keeps the (already very large) prop surface from growing further.
  // Visibility (hiding a disabled plugin's entries immediately, issue #174 AC 3)
  // is centralized in usePluginUiVisibility so it isn't recomputed per call site.
  const { pluginNavPages, settingsSidebarSections, isSectionVisible, resolveVisibleNavPage } = usePluginUiVisibility();
  const activePluginNavPage = mainView.kind === "plugin-page"
    ? resolveVisibleNavPage(mainView.pageId)
    : undefined;

  return (
    <div className="app-frame grid h-screen grid-rows-app overflow-hidden bg-transparent">
      <TitleBar
        sidebarCollapsed={sidebarCollapsed}
        windowMaximized={windowMaximized}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        canRefreshSession={canRefreshSession}
        onToggleSidebar={onToggleSidebar}
        onGoBack={onGoBack}
        onGoForward={onGoForward}
        onRefreshSession={onRefreshSession}
      />
      <div
        className={cx(
          "desktop-shell grid min-h-0 overflow-hidden bg-transparent",
          shellResizing && "sidebar-resizing cursor-col-resize select-none",
        )}
        style={{
          gridTemplateColumns: "52px minmax(0, auto) minmax(0, 1fr)",
        }}
      >
        <NavRail
          activeView={navRailActiveView}
          unreadTotal={navRailUnreadTotal}
          pluginEntries={pluginNavPages.map((page) => ({
            pageId: page.id,
            label: page.label,
            icon: page.icon,
            onSelect: () => onOpenPluginPage(page.id),
          }))}
          onOpenSearch={onOpenSearch}
          onBackToChat={onBackToChat}
          onOpenRolesWorkspace={onOpenRolesWorkspace}
          onOpenStory={onOpenStory}
          onOpenSettings={onOpenSettings}
        />
        <div
          className={cx(
            "sidebar-track relative min-h-0 overflow-hidden",
            sidebarState.animating && "transition-[width] duration-[480ms] ease-[cubic-bezier(0.22,1,0.36,1)]",
          )}
          style={{ width: sidebarState.collapsed ? 0 : sidebarState.width }}
        >
          {mainView.kind === "settings" ? (
            <SettingsSidebar
              sections={settingsSidebarSections}
              activeSection={settingsSection}
              animating={sidebarState.animating && !sidebarState.resizing}
              collapsed={sidebarState.collapsed}
              width={sidebarState.width}
              onOpenSection={onOpenSettingsSection}
              onBeginResize={sidebarState.onBeginResize}
            />
          ) : roleWorkspaceViewActive ? (
            <RoleWorkspaceSidebar
              activeSection={roleWorkspaceSection}
              animating={sidebarState.animating && !sidebarState.resizing}
              collapsed={sidebarState.collapsed}
              width={sidebarState.width}
              onOpenSection={onOpenRoleWorkspaceSection}
              onBeginResize={sidebarState.onBeginResize}
            />
          ) : (
            <RoleSidebar
              roles={roles}
              activeRoleId={activeRoleId}
              unreadCounts={unreadCounts}
              animating={sidebarState.animating && !sidebarState.resizing}
              bridgeReady={bridgeReady}
              collapsed={sidebarState.collapsed}
              width={sidebarState.width}
              onOpenRole={onOpenRole}
              onBeginResize={sidebarState.onBeginResize}
            />
          )}
        </div>
        <main className="chat-pane relative grid min-h-0 grid-cols-[minmax(0,1fr)] overflow-hidden rounded-l-lg border-b border-l border-t border-line-soft bg-[var(--chat-bg)] shadow-soft">
          {sidebarState.collapsed ? (
            <div
              className="absolute inset-y-0 left-0 z-[7] w-[3px] cursor-col-resize transition-colors hover:bg-accent-soft"
              role="separator"
              aria-orientation="vertical"
              aria-label="拖拽展开侧边栏"
              onPointerDown={sidebarState.onBeginResize}
            />
          ) : null}
          {roleWorkspaceViewActive && workspaceFeedback ? (
            <div
              className={cx(
                "absolute left-1/2 top-4 z-[6] -translate-x-1/2 rounded-md border px-4 py-2.5 text-body-sm shadow-soft",
                workspaceFeedback.tone === "success"
                  ? "border-[var(--success-300)] bg-success-soft text-success-text"
                  : "border-[var(--danger-300)] bg-danger-soft text-danger-text",
              )}
              aria-live="polite"
            >
              {workspaceFeedback.message}
            </div>
          ) : null}
          {mainView.kind === "chat" ? (
            <ChatSurface
              activeRole={activeRole}
              activeRoleId={activeRoleId}
              activeSession={activeSession}
              bridgeReady={bridgeReady}
              chatLatestImagePath={chatLatestImagePath}
              chatLatestImagePosition={chatLatestImagePosition}
              chatLatestImageSidebarAnimating={chatLatestImageSidebar.animating}
              chatLatestImageSidebarResizing={chatLatestImageSidebar.resizing}
              chatLatestImageSidebarCollapsed={chatLatestImageSidebar.collapsed}
              chatLatestImageSidebarCount={chatLatestImageSidebarCount}
              chatLatestImageSidebarWidth={chatLatestImageSidebar.width}
              currentMood={currentMood}
              moodIllustrationUrl={moodIllustrationUrl}
              roleSelfView={roleSelfView}
              relationshipTags={relationshipTags}
              lonelinessValue={lonelinessValue}
              conversationEndRef={conversationEndRef}
              headerTitle={headerTitle}
              highlightedMessageKey={highlightedMessageKey}
              onMessageNavigationTargetMounted={onMessageNavigationTargetMounted}
              notice={notice}
              sending={isVisibleChatSending}
              cancelling={isVisibleChatCancelling}
              visibleIllustrationUrl={visibleIllustrationUrl}
              windowVisible={windowVisible}
              onBeginChatLatestImageSidebarResize={chatLatestImageSidebar.beginResize}
              onGoToNextChatImage={onGoToNextChatImage}
              onGoToPreviousChatImage={onGoToPreviousChatImage}
              onOpenChatImageLightbox={onOpenChatImageLightbox}
              onOpenChatImagePreview={onOpenChatImagePreview}
              onOpenRoleDetail={onOpenRoleDetail}
              onJumpToMessage={onJumpToMessage}
              onBeginAttachmentDrag={onBeginAttachmentDrag}
              onCopyMessage={onCopyMessage}
              onSendMessage={onSendMessage}
              onCancelChat={onCancelChat}
              onLoadOlderMessages={onLoadOlderMessages}
              onToggleChatLatestImageSidebar={chatLatestImageSidebar.toggle}
            />
          ) : null}
          {mainView.kind === "roles-list" ? (
            <RoleManagementPage
              activeRoleId={activeRoleId}
              bridgeReady={bridgeReady}
              pendingCardAction={pendingRoleCardAction}
              roles={roles}
              onOpenRoleDetail={onOpenRoleManagementDetail}
              onDeleteRole={onRequestDeleteRole}
            />
          ) : null}
          {mainView.kind === "role-create" ? (
            <RoleCreatePage
              bridgeReady={bridgeReady}
              creating={creating}
              form={newRoleForm}
              onBackToList={onBackToRoleList}
              onCreateRole={onCreateNewRole}
              onResetForm={onResetNewRoleForm}
              onUpdateForm={onUpdateNewRoleForm}
              roleCardImport={roleCardImport}
              onPreviewRoleCard={onPreviewRoleCard}
              onCancelRoleCardImport={onCancelRoleCardImport}
            />
          ) : null}
          {mainView.kind === "role-detail" ? (
            <RoleDetailPage
              activeRole={detailRole}
              activeRoleId={detailRoleId}
              activeIllustration={activeIllustration}
              bridgeReady={bridgeReady}
              previewAvatar={previewAvatar}
              chatBackgroundUrl={chatBackgroundUrl}
              roleForm={roleForm}
              roleFormDirty={roleFormDirty}
              savingRole={savingRole}
              onBackToList={onBackToRoleList}
              onOpenAssetsPage={onOpenAssetsPage}
              onUpdateRoleForm={onUpdateRoleForm}
              onResetRoleForm={onResetRoleForm}
              onSaveRole={onSaveRole}
            />
          ) : null}
          {mainView.kind === "role-assets" ? (
            <RoleAssetsPage
              activeRole={detailRole}
              bridgeReady={bridgeReady}
              savingSelection={savingRoleAssets}
              roleForm={roleForm}
              selectedAvatarAsset={selectedAvatarAsset}
              selectedChatBackground={selectedChatBackground}
              onBackToDetail={onBackToRoleDetail}
              onPickAssets={onPickRoleAssets}
              onUpdateAssetOrganization={onUpdateRoleAssetOrganization}
              onRemoveAsset={onRemoveRoleAsset}
              onImportPetPackage={onImportRolePetPackage}
              onRemovePetPackage={onRemoveRolePetPackage}
              onSelectPetPackage={onSelectRolePetPackage}
              onSelectAvatarAsset={onSelectAvatarAsset}
              onSelectChatBackground={onSelectChatBackground}
              onUpdateRoleForm={onUpdateRoleForm}
              onSaveSelections={onSaveRoleAssets}
              differenceGeneration={differenceGeneration}
              onGenerateDifferences={onGenerateDifferences}
            />
          ) : null}
          {mainView.kind === "settings" ? (
            <SettingsPage
              bridgeReady={bridgeReady}
              section={settingsSection}
              isSectionVisible={isSectionVisible}
            />
          ) : null}
          {mainView.kind === "plugin-page" && activePluginNavPage ? (
            <activePluginNavPage.Component pageId={mainView.pageId} activeRoleId={activeRoleId} />
          ) : null}
        </main>
      </div>
      <RoleSearchDialog
        open={showSearchDialog}
        query={searchQuery}
        searching={searchingSessions}
        results={searchResults}
        onClose={onCloseSearchDialog}
        onSelectResult={onSelectSearchResult}
        onUpdateQuery={onUpdateSearchQuery}
      />
      <ConfirmDialog
        open={Boolean(pendingDeleteRole)}
        title="确认删除角色"
        description={pendingDeleteRole ? `“${pendingDeleteRole.name}” 删除后会移除角色会话与相关素材。` : ""}
        confirmLabel="确认删除"
        busy={deletingRole}
        onClose={onCloseDeleteDialog}
        onConfirm={onConfirmDeleteRole}
      />
      <ChatImageLightbox
        canAddToAssetLibrary={canAddToAssetLibrary}
        canGoToNext={canGoToNextLightboxImage}
        canGoToPrevious={canGoToPreviousLightboxImage}
        canLocateMessage={canLocateLightboxMessage}
        canRegenerate={canRegenerateLightboxImage}
        imagePath={chatLatestImagePath}
        addingToAssetLibrary={addingChatImageToAssetLibrary}
        regenerating={regeneratingSelectedChatImage}
        open={chatImageLightboxOpen}
        onAddToAssetLibrary={onAddSelectedChatImageToAssetLibrary}
        onClose={onCloseSelectedChatImageLightbox}
        onGoToNext={onGoToNextChatImage}
        onGoToPrevious={onGoToPreviousChatImage}
        onLocateMessage={onLocateSelectedChatImageMessage}
        onRegenerate={onRegenerateSelectedChatImage}
      />
    </div>
  );
}
