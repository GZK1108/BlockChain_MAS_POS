func checkDDoSAttack(node *Node){
	
	
		networkErrors := getNetworkErrors()
		isUsingExcess := checkExcessiveFrequency(networkErrors)
	
	
	
		resourceUsage := getNodeResourceUsage()
		isOverloading := checkForOverload(resourceUsage)
	
	
		return {isUsingExcess,isUsingExcess}
	
}