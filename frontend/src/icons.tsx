const paths: Record<string, string> = {
  compass:
    "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M16 8l-2.5 5.5L8 16l2.5-5.5L16 8Z",
  grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  route:
    "M6 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z M18 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z M8 6h8a4 4 0 0 1 0 8H8a2 2 0 0 0 0 4h8",
  calendar:
    "M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z M7 3v4 M17 3v4 M3 11h18 M7 15h3 M14 15h3",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4",
  user: "M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z M4 21v-2a8 8 0 0 1 16 0v2",
  arrow: "M4 12h16 M14 6l6 6-6 6",
  check: "M5 12l4 4L19 6",
  plus: "M12 5v14 M5 12h14",
  close: "M6 6l12 12 M18 6 6 18",
  search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14Z M15 15l6 6",
  book: "M12 5v16 M3 3c4-1 7 0 9 2 2-2 5-3 9-2v16c-4-1-7 0-9 2-2-2-5-3-9-2V3Z",
  external:
    "M14 3h7v7 M10 14 21 3 M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 7v5l3 2",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 11v6 M12 7v1",
};
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.compass} />
    </svg>
  );
}
