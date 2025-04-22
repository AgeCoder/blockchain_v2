import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card"
import Link from "next/link"
import { ArrowRight, Shield, Wallet, Database } from "lucide-react"

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="flex flex-col items-center text-center space-y-6">
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent drop-shadow">
          Secure Blockchain Wallet & Explorer
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Manage your wallet, send transactions, and explore the blockchain with a beautiful and secure interface.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mt-6">
          <Button asChild size="lg" className="px-6 py-5 text-base shadow-md hover:scale-105 transition">
            <Link href="/wallet/create">
              Create Wallet <ArrowRight className="h-4 w-4 ml-2" />
            </Link>
          </Button>
          <Button
            asChild
            variant="outline"
            size="lg"
            className="px-6 py-5 text-base hover:border-muted-foreground hover:scale-105 transition"
          >
            <Link href="/wallet/import">
              Import Wallet <Wallet className="h-4 w-4 ml-2" />
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8 mt-20">
        {[
          {
            title: "Wallet Management",
            icon: <Wallet className="h-5 w-5" />,
            desc: "Create or import wallets securely",
            content:
              "Create a new wallet or import an existing one. Your keys are stored securely in your browser only.",
            href: "/wallet/create",
            cta: "Get Started"
          },
          {
            title: "Blockchain Explorer",
            icon: <Database className="h-5 w-5" />,
            desc: "Browse blocks and transactions",
            content:
              "Explore the blockchain: view blocks, transactions, and track transaction history easily.",
            href: "/explorer",
            cta: "Explore"
          },
          {
            title: "Secure Transactions",
            icon: <Shield className="h-5 w-5" />,
            desc: "Send and receive securely",
            content:
              "Send transactions confidently. Your private keys never leave the browser and are encrypted.",
            href: "/dashboard",
            cta: "Dashboard"
          }
        ].map(({ title, icon, desc, content, href, cta }, i) => (
          <Card
            key={i}
            className="hover:shadow-xl transition-transform hover:-translate-y-1 rounded-2xl"
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                {icon} {title}
              </CardTitle>
              <CardDescription>{desc}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">{content}</p>
            </CardContent>
            <CardFooter>
              <Button asChild variant="ghost" className="gap-1 text-primary">
                <Link href={href}>
                  {cta} <ArrowRight className="h-4 w-4 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  )
}
