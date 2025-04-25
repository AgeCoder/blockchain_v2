"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Wallet, ArrowLeft, Copy, Download, Eye, EyeOff, Shield } from "lucide-react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useToast } from "@/components/ui/use-toast"
import { useWallet } from "@/lib/wallet-provider"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

export default function CreateWalletPage() {
  const { createWallet, isLoading } = useWallet()
  const router = useRouter()
  const { toast } = useToast()
  const [privateKey, setPrivateKey] = useState<string>("")
  const [showPrivateKey, setShowPrivateKey] = useState(false)
  const [step, setStep] = useState<"create" | "backup">("create")
  const [creatingWallet, setCreatingWallet] = useState(false)

  const handleCreateWallet = async () => {
    try {
      setCreatingWallet(true)
      const result = await createWallet()
      setPrivateKey(result.privateKey)
      setStep("backup")
    } catch (error) {
      console.error("Failed to create wallet:", error)
      toast({
        title: "Error",
        description: "Failed to create wallet. Please try again.",
        variant: "destructive",
      })
    } finally {
      setCreatingWallet(false)
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(privateKey)
    toast({
      title: "Copied!",
      description: "Private key copied to clipboard",
    })
  }

  const downloadPrivateKey = () => {
    const element = document.createElement("a")
    const file = new Blob([privateKey], { type: "text/plain" })
    element.href = URL.createObjectURL(file)
    element.download = `blockchain-wallet-${new Date().toISOString()}.pem`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    toast({
      title: "Downloaded",
      description: "Private key has been downloaded",
    })
  }

  const continueToWallet = () => {
    router.push("/dashboard")
  }

  if (step === "create") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="container max-w-md mx-auto px-4 py-4"
      >
        <Button variant="ghost" className="mb-6" asChild>
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
        </Button>

        <Card className="wallet-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5" /> Create New Wallet
            </CardTitle>
            <CardDescription>Generate a new blockchain wallet</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-center items-center py-2">

              <Shield className="h-28 w-28 text-primary" />

            </div>
            <p className="text-sm text-muted-foreground">
              We'll generate a new wallet for you with a secure private key. Make sure to back up your private key -
              it's the only way to access your wallet!
            </p>
          </CardContent>
          <CardFooter>
            <Button onClick={handleCreateWallet} className="w-full" disabled={isLoading || creatingWallet}>
              {creatingWallet ? (
                <>
                  <LoadingSpinner className="mr-2" />
                  Creating...
                </>
              ) : (
                "Create Wallet"
              )}
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="container max-w-md mx-auto px-4 py-12"
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5" /> Backup Your Private Key
          </CardTitle>
          <CardDescription>Save this key in a secure location</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertDescription>
              This is the only time we'll show you your private key. If you lose it, you'll lose access to your wallet
              forever.
            </AlertDescription>
          </Alert>

          <div className="relative">
            <div className="p-3 bg-muted rounded-md font-mono text-xs break-all relative">
              {showPrivateKey ? privateKey : "•".repeat(privateKey.length)}
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-2 top-2"
                onClick={() => setShowPrivateKey(!showPrivateKey)}
              >
                {showPrivateKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={copyToClipboard}>
              <Copy className="mr-2 h-4 w-4" /> Copy
            </Button>
            <Button variant="outline" className="flex-1" onClick={downloadPrivateKey}>
              <Download className="mr-2 h-4 w-4" /> Download
            </Button>
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          <Button onClick={continueToWallet} className="w-full">
            I've Backed Up My Key
          </Button>
          <p className="text-xs text-center text-muted-foreground mt-2">
            By continuing, you confirm that you've securely saved your private key.
          </p>
        </CardFooter>
      </Card>
    </motion.div>
  )
}
