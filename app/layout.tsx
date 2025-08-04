import type { Metadata, Viewport } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import './globals.css'

export const metadata: Metadata = {
  title: 'Daemon AI Assistant',
  description: 'AI assistants that live alongside your text, offering contextual suggestions and improvements',
  generator: 'Next.js',
  keywords: 'AI, writing assistant, text improvement, grammar, clarity, devil advocate',
  authors: [{ name: 'Rich Leyshon' }],
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`} style={GeistSans.style}>
      <body>{children}</body>
    </html>
  )
}
