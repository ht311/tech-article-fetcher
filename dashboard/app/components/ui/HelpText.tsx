interface HelpTextProps {
  children: React.ReactNode;
  variant?: "hint" | "preview";
}

export function HelpText({ children, variant = "hint" }: HelpTextProps) {
  if (variant === "preview") {
    return (
      <p className="mt-1 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-1">
        {children}
      </p>
    );
  }
  return <p className="mt-1 text-xs text-gray-500">{children}</p>;
}
