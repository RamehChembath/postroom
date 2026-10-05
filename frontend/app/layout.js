import "./globals.css";

export const metadata = { title: "Postroom", description: "LinkedIn strategy, writing and growth, in one place." };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
