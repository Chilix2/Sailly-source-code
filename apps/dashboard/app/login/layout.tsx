/**
 * Login Layout - No sidebar, no main nav
 * Minimal layout for authentication page
 */

export default function LoginLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
