'use client'
import React, { useEffect, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { Search, Database, Clock, Copy, ChevronRight, Loader2, HardDrive, Layers, Hash, Coins, ArrowRightLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { useToast } from "@/components/ui/use-toast"
import { debounce } from "lodash"
import { useInfiniteScroll } from "@/hooks/use-infinite-scroll"

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

const ExplorerPage = () => {
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
    toast({ title: "Copied to clipboard", description: "The content has been copied to your clipboard." })
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

  const totalTransactions = blocks.reduce((acc, block) => acc + block.data.length, 0)
  const latestDifficulty = blocks.length > 0 ? blocks[0].difficulty : 3
  const displayedBlocks = searchResults.length > 0 ? searchResults : blocks
  const blockchainProgress = blockchainLength > 0 ? (blocks.length / blockchainLength) * 100 : 0

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-full md:w-96" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-6 w-6 rounded-full" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-32 mt-2" />
                <Skeleton className="h-4 w-full mt-4" />
              </CardContent>
            </Card>
          ))}
        </div>

        <Skeleton className="h-10 w-48 mb-6" />
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <TooltipProvider>
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              Blockchain Explorer
            </h1>
            <p className="text-muted-foreground mt-1">
              Explore transactions, blocks, and network activity
            </p>
          </div>
          <div className="relative w-full md:w-auto">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by block, tx, address..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 w-full md:w-96 bg-background/50 backdrop-blur-sm"
            />
          </div>
        </div>



        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-background to-muted/50 border-primary/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Blocks
              </CardTitle>
              <Layers className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{blockchainLength}</div>
              <p className="text-xs text-muted-foreground mt-1">
                +{blocks.length > 0 ? formatDistanceToNow(new Date(blocks[0].timestamp / 1_000_000), { addSuffix: true }) : 'N/A'}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-background to-muted/50 border-primary/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Transactions
              </CardTitle>
              <ArrowRightLeft className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalTransactions}</div>
              <p className="text-xs text-muted-foreground mt-1">
                ~{(totalTransactions / blockchainLength).toFixed(1)} tx/block
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-background to-muted/50 border-primary/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Network Difficulty
              </CardTitle>
              <Hash className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{latestDifficulty}</div>
              <Progress value={Math.min(latestDifficulty * 10, 100)} className="h-2 mt-2" />
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">
            {searchResults.length > 0 ? 'Search Results' : 'Latest Blocks'}
          </h2>
          {blocks.length > 0 && (
            <Badge variant="outline" className="px-3 py-1 text-sm">
              Synced {blocks.length} of {blockchainLength} blocks
            </Badge>
          )}
        </div>

        {isSearching ? (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Searching blockchain...</p>
          </div>
        ) : displayedBlocks.length === 0 ? (
          <Card className="bg-background/50 backdrop-blur-sm">
            <CardContent className="flex flex-col items-center justify-center py-12 gap-4">
              <Database className="h-10 w-10 text-muted-foreground" />
              <p className="text-muted-foreground">No blocks found</p>
              {searchQuery && (
                <Button variant="outline" onClick={() => setSearchQuery('')}>
                  Clear search
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {displayedBlocks.map((block) => {
              const totalFees = block.data
                .filter((tx: Transaction) => tx.is_coinbase)
                .reduce((acc, tx) => acc + (tx.input.fees || 0), 0)
              const timestamp = new Date(block.timestamp / 1_000_000)

              return (
                <Card
                  key={block.hash}
                  className="transition-all hover:border-primary/50 hover:shadow-lg cursor-pointer bg-background/50 backdrop-blur-sm"
                  onClick={() => viewBlockDetails(block)}
                >
                  <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                      <div className="md:col-span-2 flex items-center gap-3">
                        <div className="bg-primary/10 p-2 rounded-full">
                          <HardDrive className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">Block {block.height}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDistanceToNow(timestamp, { addSuffix: true })}
                          </p>
                        </div>
                      </div>

                      <div className="md:col-span-6">
                        <div className="flex flex-col gap-2">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div
                                className="flex items-center gap-2 font-mono text-sm hover:text-primary transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(block.hash)
                                }}
                              >
                                <span className="truncate">{block.hash}</span>
                                <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Block hash</p>
                            </TooltipContent>
                          </Tooltip>

                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div
                                className="flex items-center gap-2 font-mono text-sm text-muted-foreground hover:text-primary transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(block.last_hash)
                                }}
                              >
                                <span className="truncate">Prev: {block.last_hash}</span>
                                <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Previous block hash</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      </div>

                      <div className="md:col-span-2">
                        <Badge variant="secondary" className="px-3 py-1">
                          {block.data.length} {block.data.length === 1 ? 'tx' : 'txs'}
                        </Badge>
                      </div>

                      <div className="md:col-span-2 flex justify-end">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation()
                            viewBlockDetails(block)
                          }}
                        >
                          Details
                          <ChevronRight className="ml-1 h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {blocks.length < blockchainLength && !searchResults.length && (
          <div ref={observerRef} className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}

export default ExplorerPage