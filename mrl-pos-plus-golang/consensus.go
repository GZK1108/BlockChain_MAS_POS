package main

import (
	"math/rand"
	"time"
)

// pickWinner creates a lottery pool of validators and chooses the validator who gets to forge a block to the blockchain
// by random selecting from the pool, weighted by amount of tokens staked
func pickWinner() {
	time.Sleep(3 * time.Second)
	mutex.Lock()
	temp := tempBlocks
	mutex.Unlock()

	lotteryPool := []string{}
	if len(temp) > 0 {

		// slightly modified traditional proof of stake algorithm
		// from all validators who submitted a block, weight them by the number of staked tokens
		// in traditional proof of stake, validators can participate without submitting a block to be forged
	OUTER:
		for _, block := range temp {
			// if already in lottery pool, skip
			for _, node := range lotteryPool {
				if block.Validator == node {
					continue OUTER
				}
			}

			// lock list of validators to prevent data race
			mutex.Lock()
			setValidators := validators
			mutex.Unlock()

			k, ok := setValidators[block.Validator]
			if ok {
				for i := 0; i < k; i++ {
					lotteryPool = append(lotteryPool, block.Validator)
				}
			}
		}

		// randomly pick winner from lottery pool
		s := rand.NewSource(time.Now().Unix())
		r := rand.New(s)
		lotteryWinner := electValidator(lotteryPool)

		// add block of winner to blockchain and let all the other nodes know
		for _, block := range temp {
			if block.Validator == lotteryWinner {
				mutex.Lock()
				Blockchain = append(Blockchain, block)
				mutex.Unlock()
				for _ = range validators {
					announcements <- "\nwinning validator: " + lotteryWinner + "\n"
				}
				break
			}
		}
	}

	mutex.Lock()
	tempBlocks = []Block{}
	mutex.Unlock()
}

func ElectValidator(agents []Agent) Agent {
	var electedAgents []struct {
		agent      Agent
		agentScore float64
	}

	for _, agent := range agents {
		attackProbability := getTotalAttackProbability(agent)
		lastAttackAttempt := agent.attackAge

		if attackProbability*float64(lastAttackAttempt) >= 2.0 {
			agent.attackAge--
			break
		}

		tempScore := -1 * attackProbability * float64(lastAttackAttempt) * agent.stake

		electedAgents = append(electedAgents, struct {
			agent      Agent
			agentScore float64
		}{agent, tempScore})

		if agent.attackAge > 0 {
			agent.attackAge--
		}
	}

	// Sorting the electedAgents based on agentScore
	sortByAgentScore(electedAgents)

	if electedAgents[0].agent.stake == electedAgents[1].agent.stake {
		var eqAgents []Agent

		for _, agent := range electedAgents {
			if agent.agent.stake == electedAgents[0].agent.stake {
				eqAgents = append(eqAgents, agent.agent)
			}
		}

		randIndex := rand.Intn(len(eqAgents))
		return eqAgents[randIndex]
	}

	return electedAgents[0].agent
}

// sortByAgentScore sorts the electedAgents slice by agentScore in ascending order
func sortByAgentScore(electedAgents []struct {
	agent      Agent
	agentScore float64
}) {
	for i := 0; i < len(electedAgents); i++ {
		for j := i + 1; j < len(electedAgents); j++ {
			if electedAgents[i].agentScore > electedAgents[j].agentScore {
				// Swap
				electedAgents[i], electedAgents[j] = electedAgents[j], electedAgents[i]
			}
		}
	}
}
