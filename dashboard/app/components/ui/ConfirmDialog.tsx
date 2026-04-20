"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "destructive" | "default";
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "実行する",
  cancelLabel = "キャンセル",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 animate-in fade-in-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl animate-in fade-in-0 zoom-in-95">
          <DialogPrimitive.Title className="text-base font-semibold text-gray-900">
            {title}
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-2 text-sm text-gray-500">
            {description}
          </DialogPrimitive.Description>
          <div className="mt-5 flex justify-end gap-3">
            <DialogPrimitive.Close asChild>
              <button
                type="button"
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                {cancelLabel}
              </button>
            </DialogPrimitive.Close>
            <button
              type="button"
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
              className={
                variant === "destructive"
                  ? "px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700"
                  : "px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              }
            >
              {confirmLabel}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
