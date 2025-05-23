package main

import (
	"sync"
)

// Block represents each 'item' in the blockchain
type Block struct {
	Index     int
	Timestamp string
	Mileage   int
	Hash      string
	PrevHash  string
	Validator string
}

type Node struct {
	blocksGenerated int
	hashRate        float64
	averageHashRate float64
	forks           int
	reputation      []int
}

// Blockchain is a series of validated Blocks
var Blockchain []Block
var tempBlocks []Block

// candidateBlocks handles incoming blocks for validation
var candidateBlocks = make(chan Block)

// announcements broadcasts winning validator to all nodes
var announcements = make(chan string)

var mutex = &sync.Mutex{}

// validators keeps track of open validators and balances
var validators = make(map[string]int)
