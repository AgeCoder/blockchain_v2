'use client'
import React, { useEffect, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { Search, Database, Clock, Copy, ChevronRight, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { api } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { useToast } from "@/components/ui/use-toast"
import { debounce } from "lodash"
import { useInfiniteScroll } from "@/hooks/use-infinite-scroll"

// Types aligned with backend schema
interface Transaction {
  id: string
  is_coinbase: boolean
  input: { address: string; fees?: number; subsidy?: number }
  output: Record<string, number>
  fee: number
  size: number
}

interface Block {
  hash: string
  height: number
  timestamp: number
  data: Transaction[]
  nonce: number
  last_hash: string
  difficulty: number
  version: number
  merkle_root: string
  tx_count: number
}

interface BlockchainResponse {
  chain: Block[]
  utxo_set: Record<string, any>
  current_height: number
}

const useDebounce = <T extends (...args: any[]) => any>(callback: T, delay: number) => {
  return useMemo(() => debounce(callback, delay), [callback, delay])
}

export default function ExplorerPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(true)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [blockchainLength, setBlockchainLength] = useState(0)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<Block[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const fetchBlockchainData = useCallback(async () => {
    setIsLoading(true)
    try {
      const lengthResponse = await api.blockchain.getLength()
      setBlockchainLength(lengthResponse.length)
      const response = await api.blockchain.getRange(0, 10)
      setBlocks(response)
    } catch (error) {
      console.error("Error fetching blockchain data:", error)
      toast({
        title: "Error",
        description: "Failed to load blockchain data",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  const fetchMoreBlocks = useCallback(async () => {
    if (blocks.length >= blockchainLength) return
    try {
      const newStart = blocks.length
      const newEnd = Math.min(newStart + 10, blockchainLength)
      const response = await api.blockchain.getRange(newStart, newEnd)
      setBlocks((prev) => [...prev, ...response])
    } catch (error) {
      console.error("Error fetching more blocks:", error)
      toast({
        title: "Error",
        description: "Failed to load more blocks",
        variant: "destructive",
      })
    }
  }, [blocks.length, blockchainLength, toast])

  const { observerRef } = useInfiniteScroll(fetchMoreBlocks, { isLoading: isLoading || isSearching })

  const handleSearch = useCallback(
    async (query: string) => {
      if (!query.trim()) {
        setSearchResults([])
        setIsSearching(false)
        return
      }
      setIsSearching(true)
      try {
        const response = await api.blockchain.getAll()
        const blocks = response.chain
        const results = blocks.filter(
          (block: Block) =>
            block.hash.includes(query) ||
            block.height.toString() === query ||
            block.last_hash.includes(query) ||
            block.data.some((tx: Transaction) => tx.id.includes(query) || Object.keys(tx.output).includes(query))
        ).slice(0, 5)
        setSearchResults(results)
      } catch (error) {
        console.error("Error searching blocks:", error)
        toast({
          title: "Error",
          description: "Failed to search blocks",
          variant: "destructive",
        })
      } finally {
        setIsSearching(false)
      }
    },
    [toast]
  )

  const debouncedSearch = useDebounce(handleSearch, 300)

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
    toast({ title: "Copied", description: "Text copied to clipboard" })
  }, [toast])

  const viewBlockDetails = useCallback(
    (block: Block) => {
      router.push(`/explorer/block/${block.height}`)
    },
    [router]
  )

  useEffect(() => {
    fetchBlockchainData()
  }, [fetchBlockchainData])

  useEffect(() => {
    debouncedSearch(searchQuery)
  }, [searchQuery, debouncedSearch])

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8" role="region" aria-label="Loading blockchain explorer">
        <Skeleton className="h-12 w-full max-w-md mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
        <Skeleton className="h-8 w-48 mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-[200px]" />
          ))}
        </div>
      </div>
    )
  }

  const displayedBlocks = searchResults.length > 0 ? searchResults : blocks
  const totalTransactions = blocks.reduce((acc, block) => acc + block.data.length, 0)
  const latestDifficulty = blocks.length > 0 ? blocks[0].difficulty : 3

  return (
    <TooltipProvider>
      <div className="container mx-auto px-4 py-8" role="main" aria-label="Blockchain Explorer">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <h1 className="text-3xl font-bold">Blockchain Explorer</h1>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSearch(searchQuery)
            }}
            className="w-full md:w-auto"
          >
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search by block hash, height, tx ID, or address..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 w-full md:w-[400px]"
                aria-label="Search blocks and transactions"
              />
            </div>
          </form>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl">{blockchainLength}</CardTitle>
              <CardDescription>Total Blocks</CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl">{totalTransactions}</CardTitle>
              <CardDescription>Total Transactions</CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-2xl">{latestDifficulty}</CardTitle>
              <CardDescription>Current Difficulty</CardDescription>
            </CardHeader>
          </Card>
        </div>

        <h2 className="text-2xl font-bold mb-4">Latest Blocks</h2>

        {isSearching ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" aria-label="Searching blocks" />
          </div>
        ) : displayedBlocks.length === 0 ? (
          <p className="text-center text-muted-foreground">No blocks found</p>
        ) : (
          <Table role="grid" aria-label="Blocks table">
            <TableHeader>
              <TableRow>
                <TableHead>Height</TableHead>
                <TableHead>Hash</TableHead>
                <TableHead>Previous Hash</TableHead>
                <TableHead>Transactions</TableHead>
                <TableHead>Fees</TableHead>
                <TableHead>Time</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayedBlocks.map((block) => {
                const totalFees = block.data
                  .filter((tx: Transaction) => tx.is_coinbase)
                  .reduce((acc, tx) => acc + (tx.input.fees || 0), 0)
                return (
                  <TableRow
                    key={block.hash}
                    role="row"
                    tabIndex={0}
                    onClick={() => viewBlockDetails(block)}
                    onKeyDown={(e) => e.key === "Enter" && viewBlockDetails(block)}
                    className="cursor-pointer hover:bg-muted"
                  >
                    <TableCell>{block.height}</TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger>
                          <span
                            className="font-mono truncate max-w-[150px] inline-block"
                            onClick={(e) => {
                              e.stopPropagation()
                              copyToClipboard(block.hash)
                            }}
                          >
                            {block.hash}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          {block.hash}
                          <Copy className="h-4 w-4 ml-2 inline" aria-hidden="true" />
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger>
                          <span
                            className="font-mono truncate max-w-[150px] inline-block"
                            onClick={(e) => {
                              e.stopPropagation()
                              copyToClipboard(block.last_hash)
                            }}
                          >
                            {block.last_hash}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          {block.last_hash}
                          <Copy className="h-4 w-4 ml-2 inline" aria-hidden="true" />
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell>{block.data.length}</TableCell>
                    <TableCell>{totalFees.toFixed(6)}</TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(block.timestamp / 1_000_000), { addSuffix: true })}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          viewBlockDetails(block)
                        }}
                        aria-label={`View details for block ${block.height}`}
                      >
                        Details <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}

        {blocks.length < blockchainLength && !searchResults.length && (
          <div ref={observerRef} className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" aria-label="Loading more blocks" />
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}