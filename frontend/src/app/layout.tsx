import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: 'Policy Attestation',
  description: 'Publish policies, collect attestations, prove who agreed to what.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="top">
          <strong>Policy Attestation</strong>
          <div>
            <Link href="/">My policies</Link>
            <Link href="/admin">Admin</Link>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  )
}
