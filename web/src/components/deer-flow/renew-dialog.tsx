// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { closeRenewDialog, useAuthStore } from "~/core/store";

import { RenewForm } from "./renew-form";

/**
 * Global dialog popped when the server answers 402 (out of quota).
 */
export function RenewDialog() {
  const open = useAuthStore((state) => state.renewDialogOpen);
  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!value) {
          closeRenewDialog();
        }
      }}
    >
      <DialogContent className="w-[92vw] max-w-md rounded-xl">
        <DialogHeader>
          <DialogTitle>剩余次数用完啦</DialogTitle>
          <DialogDescription>
            联系卖家购买新卡密，输入后立即恢复使用。放心，未完成的任务不会扣次数。
          </DialogDescription>
        </DialogHeader>
        <RenewForm autoFocus onSuccess={closeRenewDialog} />
      </DialogContent>
    </Dialog>
  );
}
