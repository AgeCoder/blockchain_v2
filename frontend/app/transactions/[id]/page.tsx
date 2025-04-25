"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import {
    ArrowLeft,
    Send,
    ReceiptIcon as Receive,
    BarChart2,
    Clock,
    Copy,
    ExternalLink,
    CheckCircle,
    AlertCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/components/ui/use-toast"

// Mock transaction data
const transactions = [
    {
        id: "tx1",
        type: "send",
        amount: "10.5",
        to: "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
        from: "0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
        date: "2023-04-22T14:30:00Z",
        status: "completed",
        hash: "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        fee: "0.001",
        blockNumber: 12345678,
        confirmations: 24,
    },
    {
        id: "tx2",
        type: "receive",
        amount: "25.0",
        from: "0x5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e",
        to: "0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
        date: "2023-04-21T10:15:00Z",
        status: "completed",
        hash: "0x0987654321fedcba0987654321fedcba0987654321fedcba0987654321fedcba",
        fee: "0.001",
        blockNumber: 12345670,
        confirmations: 32,
    },
    {
        id: "tx3",
        type: "mine",
        amount: "5.0",
        to: "0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
        date: "2023-04-20T08:45:00Z",
        status: "completed",
        hash: "0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1a2b3c4d5e6f7a8b9c0d1e2f",
        fee: "0",
        blockNumber: 12345665,
        confirmations: 37,
    },
    {
        id: "tx4",
        type: "send",
        amount: "3.25",
        to: "0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c",
        from: "0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
        date: "2023-04-19T16:20:00Z",
        status: "completed",
        hash: "0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2b3c4d5e6f7a8b9c0d1e2f3",
        fee: "0.001",
        blockNumber: 12345660,
        confirmations: 42,
    },
    {
        id: "tx5",
        type: "receive",
        amount: "12.75",
        from: "0x3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d",
        to: "0x9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
        date: "2023-04-18T09:10:00Z",
        status: "completed",
        hash: "0x3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3c4d5e6f7a8b9c0d1e2f3a4",
        fee: "0.001",
        blockNumber: 12345655,
        confirmations: 47,
    },
]

export default function TransactionDetailPage() {
    const params = useParams()
    const { id } = params
    const [transaction, setTransaction] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const { toast } = useToast()

    useEffect(() => {
        // Simulate API call to fetch transaction details
        setTimeout(() => {
            const tx = transactions.find((tx) => tx.id === id)
            setTransaction(tx || null)
            setLoading(false)
        }, 500)
    }, [id])

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        })
    }

    const handleCopy = (text: string, label: string) => {
        navigator.clipboard.writeText(text)
        toast({
            title: "Copied to clipboard",
            description: `${label} has been copied to clipboard.`,
        })
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="flex flex-col items-center gap-2">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
                    <p className="text-sm text-muted-foreground">Loading transaction details...</p>
                </div>
            </div>
        )
    }

    if (!transaction) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh]">
                <AlertCircle className="h-12 w-12 text-destructive mb-4" />
                <h2 className="text-2xl font-bold mb-2">Transaction Not Found</h2>
                <p className="text-muted-foreground mb-6">
                    The transaction you're looking for doesn't exist or has been removed.
                </p>
                <Button asChild>
                    <Link href="/transactions">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Transactions
                    </Link>
                </Button>
            </div>
        )
    }

    return (
        <div className="max-w-3xl mx-auto wallet-section">
            <Button variant="ghost" className="mb-6" asChild>
                <Link href="/transactions">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Transactions
                </Link>
            </Button>

            <Card className="wallet-card">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div
                                className={`p-2 rounded-full ${transaction.type === "send"
                                    ? "bg-red-100 text-red-600"
                                    : transaction.type === "receive"
                                        ? "bg-green-100 text-green-600"
                                        : "bg-blue-100 text-blue-600"
                                    }`}
                            >
                                {transaction.type === "send" ? (
                                    <Send className="h-5 w-5" />
                                ) : transaction.type === "receive" ? (
                                    <Receive className="h-5 w-5" />
                                ) : (
                                    <BarChart2 className="h-5 w-5" />
                                )}
                            </div>
                            <div>
                                <CardTitle className="capitalize">{transaction.type} Transaction</CardTitle>
                                <CardDescription>{formatDate(transaction.date)}</CardDescription>
                            </div>
                        </div>
                        <Badge
                            variant={transaction.status === "completed" ? "outline" : "secondary"}
                            className={transaction.status === "completed" ? "bg-green-100 text-green-600 hover:bg-green-100" : ""}
                        >
                            {transaction.status === "completed" && <CheckCircle className="mr-1 h-3 w-3" />}
                            {transaction.status}
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="flex flex-col items-center justify-center py-6 px-4 bg-muted/30 rounded-lg">
                        <p className="text-sm text-muted-foreground mb-1">
                            {transaction.type === "send" ? "Amount Sent" : "Amount Received"}
                        </p>
                        <div className="flex items-baseline">
                            <span className={`text-3xl font-bold ${transaction.type === "send" ? "text-red-600" : "text-green-600"}`}>
                                {transaction.type === "send" ? "-" : "+"}
                                {transaction.amount}
                            </span>
                            <span className="ml-2 text-lg">COIN</span>
                        </div>
                        {transaction.type === "send" && (
                            <p className="text-sm text-muted-foreground mt-2">Fee: {transaction.fee} COIN</p>
                        )}
                    </div>

                    <div className="space-y-4">
                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">Transaction Hash</span>
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-mono break-all">{transaction.hash}</span>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6"
                                    onClick={() => handleCopy(transaction.hash, "Transaction hash")}
                                >
                                    <Copy className="h-3 w-3" />
                                    <span className="sr-only">Copy hash</span>
                                </Button>
                            </div>
                        </div>

                        <Separator />

                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">Status</span>
                            <span className="text-sm capitalize">{transaction.status}</span>
                        </div>

                        <Separator />

                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">Block</span>
                            <Link
                                href={`/explorer/block/${transaction.blockNumber}`}
                                className="text-sm text-primary hover:underline flex items-center"
                            >
                                {transaction.blockNumber}
                                <ExternalLink className="ml-1 h-3 w-3" />
                            </Link>
                        </div>

                        <Separator />

                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">Confirmations</span>
                            <span className="text-sm">{transaction.confirmations}</span>
                        </div>

                        <Separator />

                        {transaction.type !== "mine" && (
                            <>
                                <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                                    <span className="text-sm font-medium">From</span>
                                    <div className="flex items-center gap-2">
                                        <Link
                                            href={`/explorer/address/${transaction.from}`}
                                            className="text-sm font-mono text-primary hover:underline break-all"
                                        >
                                            {transaction.from}
                                        </Link>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={() => handleCopy(transaction.from, "From address")}
                                        >
                                            <Copy className="h-3 w-3" />
                                            <span className="sr-only">Copy address</span>
                                        </Button>
                                    </div>
                                </div>

                                <Separator />
                            </>
                        )}

                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">To</span>
                            <div className="flex items-center gap-2">
                                <Link
                                    href={`/explorer/address/${transaction.to}`}
                                    className="text-sm font-mono text-primary hover:underline break-all"
                                >
                                    {transaction.to}
                                </Link>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6"
                                    onClick={() => handleCopy(transaction.to, "To address")}
                                >
                                    <Copy className="h-3 w-3" />
                                    <span className="sr-only">Copy address</span>
                                </Button>
                            </div>
                        </div>

                        <Separator />

                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">Transaction Fee</span>
                            <span className="text-sm">{transaction.fee} COIN</span>
                        </div>

                        <Separator />

                        <div className="flex flex-col sm:flex-row justify-between py-2 gap-2">
                            <span className="text-sm font-medium">Date</span>
                            <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3 text-muted-foreground" />
                                <span className="text-sm">{formatDate(transaction.date)}</span>
                            </div>
                        </div>
                    </div>
                </CardContent>
                <CardFooter className="flex justify-between">
                    <Button variant="outline" asChild>
                        <Link href={`/explorer/tx/${transaction.hash}`}>
                            View in Explorer
                            <ExternalLink className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>

                    {transaction.type === "receive" && (
                        <Button asChild>
                            <Link href="/transactions/send">
                                <Send className="mr-2 h-4 w-4" />
                                Send Coins
                            </Link>
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </div>
    )
}
