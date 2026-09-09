import { useState, type ComponentProps } from "react";

type DesktopExternalLinkProps = Omit<ComponentProps<"a">, "href" | "onClick"> & { href: string };

/** Opens an external destination through Electron and exposes shell failures inline. */
export function DesktopExternalLink({ href, children, ...props }: DesktopExternalLinkProps) {
  const [error, setError] = useState<string | null>(null);

  async function open() {
    setError(null);
    try {
      const result = await window.miraDesktop.openExternal(href);
      if (!result.ok) throw new Error(result.error ?? "无法打开链接");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  return (
    <>
      <a {...props} href={href} onClick={(event) => { event.preventDefault(); void open(); }}>{children}</a>
      {error ? <span role="alert" className="block break-words text-sm text-danger-text">{error}</span> : null}
    </>
  );
}
