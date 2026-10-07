/** AAOS adapters based on selected shadcn structure and Radix interactions.
 * Upstream snapshots and MIT notices are recorded in THIRD_PARTY_NOTICES.md.
 */
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import "./primitives.css";

function classes(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  busy?: boolean;
  disabledReason?: string;
};

export const AaosButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function AaosButton({ variant = "secondary", busy, disabledReason, disabled, className, children, type = "button", ...props }, ref) {
    const blocked = Boolean(disabled || busy);
    return <button {...props} ref={ref} type={type} className={classes("aaos-button", className)} data-variant={variant}
      aria-busy={busy || undefined} aria-description={disabledReason} disabled={blocked} title={disabledReason || props.title}>
      {children}{busy ? <span className="aaos-sr-only">，处理中</span> : null}
      {blocked && disabledReason ? <small aria-hidden="true" className="aaos-action-reason"> · {disabledReason}</small> : null}
    </button>;
  },
);

type FieldProps = React.InputHTMLAttributes<HTMLInputElement> & { label: string; labelClassName?: string; help?: string; error?: string };
export const AaosField = React.forwardRef<HTMLInputElement, FieldProps>(
  function AaosField({ label, labelClassName, help, error, id, className, ...props }, ref) {
    const generated = React.useId();
    const inputId = id ?? generated;
    const described = [props["aria-describedby"], help ? `${inputId}-help` : undefined, error ? `${inputId}-error` : undefined].filter(Boolean).join(" ") || undefined;
    return <div className="aaos-field">
      <label className={labelClassName} htmlFor={inputId}>{label}</label>
      <input {...props} ref={ref} id={inputId} className={classes("aaos-input", className)} aria-invalid={error ? true : props["aria-invalid"]} aria-describedby={described} />
      {help ? <p id={`${inputId}-help`} className="aaos-help">{help}</p> : null}
      {error ? <p id={`${inputId}-error`} className="aaos-error" role="alert">{error}</p> : null}
    </div>;
  },
);

type DialogProps = {
  title: string;
  description: string;
  trigger: React.ReactElement;
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  overlayClassName?: string;
  contentClassName?: string;
  onOpenAutoFocus?: (event: Event) => void;
  onCloseAutoFocus?: (event: Event) => void;
};

export function AaosDialog({ title, description, trigger, children, open, onOpenChange, overlayClassName, contentClassName, onOpenAutoFocus, onCloseAutoFocus }: DialogProps) {
  return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
    <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger>
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className={classes("aaos-dialog-overlay", overlayClassName)} />
      <DialogPrimitive.Content className={classes("aaos-dialog-content", contentClassName)} onOpenAutoFocus={onOpenAutoFocus} onCloseAutoFocus={onCloseAutoFocus}>
        <DialogPrimitive.Title className="aaos-dialog-title">{title}</DialogPrimitive.Title>
        <DialogPrimitive.Description className="aaos-help">{description}</DialogPrimitive.Description>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>;
}

type TabsProps = {
  value: string;
  onValueChange: (value: string) => void;
  label: string;
  tabs: ReadonlyArray<{ id: string; label: string; content: React.ReactNode; disabled?: boolean }>;
};

export function AaosTabs({ value, onValueChange, label, tabs }: TabsProps) {
  return <TabsPrimitive.Root value={value} onValueChange={onValueChange} activationMode="manual">
    <TabsPrimitive.List aria-label={label} className="aaos-tabs-list">
      {tabs.map((tab) => <TabsPrimitive.Trigger key={tab.id} value={tab.id} disabled={tab.disabled} className="aaos-tab">{tab.label}</TabsPrimitive.Trigger>)}
    </TabsPrimitive.List>
    {tabs.map((tab) => <TabsPrimitive.Content key={tab.id} value={tab.id} className="aaos-tab-panel">{tab.content}</TabsPrimitive.Content>)}
  </TabsPrimitive.Root>;
}
