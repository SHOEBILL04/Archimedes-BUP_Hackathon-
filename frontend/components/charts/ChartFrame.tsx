import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

interface ChartFrameProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  /** Optional right-aligned chip in the header. */
  action?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * Shared shell for every chart card, so heading rhythm, padding and plot
 * height stay identical across the dashboard.
 */
export function ChartFrame({
  title,
  description,
  icon,
  action,
  children,
}: ChartFrameProps) {
  return (
    <Card className="flex h-full flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm">
              {icon}
              <span>{title}</span>
            </CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          {action}
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-6 pt-2">
        <div className="h-[280px] w-full">{children}</div>
      </CardContent>
    </Card>
  );
}
