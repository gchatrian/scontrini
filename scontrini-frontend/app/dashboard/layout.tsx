'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { LogOut, Home, Upload, Receipt, Users, Settings } from 'lucide-react'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Navigation Bar */}
      <nav className="bg-white border-b sticky top-0 z-10 shadow-sm">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/dashboard" className="flex items-center space-x-2">
              <span className="text-2xl">🧾</span>
              <span className="text-xl font-bold">Scontrini</span>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center space-x-1">
              <NavLink href="/dashboard" icon={<Home className="w-4 h-4" />}>
                Dashboard
              </NavLink>
              <NavLink href="/upload" icon={<Upload className="w-4 h-4" />}>
                Carica
              </NavLink>
              <NavLink href="/receipts" icon={<Receipt className="w-4 h-4" />}>
                Scontrini
              </NavLink>
              <NavLink href="/household" icon={<Users className="w-4 h-4" />}>
                Famiglia
              </NavLink>
            </div>

            {/* User Menu */}
            <div className="flex items-center space-x-4">
              <div className="hidden md:block text-sm">
                <p className="font-medium">{user?.email}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={signOut}
              >
                <LogOut className="w-4 h-4 mr-2" />
                Esci
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile Nav */}
      <div className="md:hidden bg-white border-t fixed bottom-0 left-0 right-0 z-10">
        <div className="grid grid-cols-4 gap-1 p-2">
          <MobileNavLink href="/dashboard" icon={<Home className="w-5 h-5" />}>
            Home
          </MobileNavLink>
          <MobileNavLink href="/upload" icon={<Upload className="w-5 h-5" />}>
            Carica
          </MobileNavLink>
          <MobileNavLink href="/receipts" icon={<Receipt className="w-5 h-5" />}>
            Storico
          </MobileNavLink>
          <MobileNavLink href="/household" icon={<Users className="w-5 h-5" />}>
            Famiglia
          </MobileNavLink>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 pb-24 md:pb-8">
        {children}
      </main>
    </div>
  )
}

// Desktop Nav Link Component
function NavLink({
  href,
  icon,
  children,
}: {
  href: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Link href={href}>
      <Button variant="ghost" className="flex items-center space-x-2">
        {icon}
        <span>{children}</span>
      </Button>
    </Link>
  )
}

// Mobile Nav Link Component
function MobileNavLink({
  href,
  icon,
  children,
}: {
  href: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Link href={href} className="flex flex-col items-center justify-center py-2 text-xs hover:bg-muted rounded-lg transition-colors">
      {icon}
      <span className="mt-1">{children}</span>
    </Link>
  )
}