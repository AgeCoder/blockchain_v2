"use client"

import type React from "react"
import { useState } from "react"
import Link from "next/link"
import { ArrowLeft, Wallet, AlertCircle } from "lucide-react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useWallet } from "@/lib/wallet-provider"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

export default function ImportWalletPage() {
  const [privateKey, setPrivateKey] = useState("")
  const { importWallet, isLoading } = useWallet()
  const [error, setError] = useState("")
  const [importing, setImporting] = useState(false)

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!privateKey.trim()) {
      setError("Please enter your private key")
      return
    }

    try {
      setImporting(true)
      await importWallet(privateKey)
    } catch (err) {
      setError("Invalid private key. Please check and try again.")
    } finally {
      setImporting(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="container max-w-md mx-auto px-4 py-12"
    >
      <Link href="/" className="flex items-center text-sm mb-8 hover:underline">
        <ArrowLeft className="mr-2 h-4 w-4" /> Back to home
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5" /> Import Wallet
          </CardTitle>
          <CardDescription>Import an existing wallet using your private key</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleImport} className="space-y-4">
            <div className="space-y-2">
              <Textarea
                placeholder="Paste your private key here"
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                className="font-mono h-32"
                aria-label="Private key"
              />
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4 mr-2" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>
          </form>
        </CardContent>
        <CardFooter>
          <Button onClick={handleImport} className="w-full" disabled={isLoading || importing || !privateKey.trim()}>
            {importing ? (
              <>
                <LoadingSpinner className="mr-2" />
                Importing...
              </>
            ) : (
              "Import Wallet"
            )}
          </Button>
        </CardFooter>
      </Card>
    </motion.div>
  )
}
