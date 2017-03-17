# File name: dataflowanalysis.py
# Author: Nupur Garg
# Date created: 1/31/2017
# Python Version: 3.5


import copy

from src.globals import *
from src.models.blockinfo import *


class IterativeDataflowAnalysis(ABC):
    """
    Abstract class to perform dataflow analysis.

    block_info_type: NodeInformation
        NodeInformation class.
    """

    def __init__(self, block_info_type):
        self.block_info_type = block_info_type

    # Performs the analysis.
    def analyze(self, func_block):
        # Initialize FunctionBlock.
        info = FunctionBlockInformation()
        info.init(func_block, self.block_info_type)

        # Compute gen and kill maps.
        func_gen = self._compute_func_gen(info)
        self._compute_gen_kill(info, func_gen)

        # Compute in and out maps.
        sorted_blocks = self._get_sorted_blocks(func_block)
        info_cpy = None
        while info != info_cpy:
            info_cpy = copy.deepcopy(info)
            self._compute_info(info, sorted_blocks)

        return info

    # Compute the gen map for a function.
    def _compute_func_gen(self, func_block_info):
        func_gen = {}
        for block, info in func_block_info.blocks():
            for instruction in block.get_instructions():
                for variable in instruction.defined:
                    if not variable in func_gen:
                        func_gen[variable] = set()
                    func_gen[variable].add((block.label, instruction.lineno))
        return func_gen

    # Compute gen and kill maps for each block.
    def _compute_gen_kill(self, func_block_info, func_gen):
        for block, info in func_block_info.blocks():
            # Generate gen map for given block.
            for instruction in block.get_instructions():
                for variable in instruction.defined:
                    info.gen[variable] = set([(block.label, instruction.lineno)])

                # Generate gen and kill map for given instruction.
                instr_info = func_block_info.get_instruction_info(instruction.lineno)
                instr_info.gen = {var: set([(block.label, instruction.lineno)])
                                  for var in instruction.defined}
                instr_info.kill = NodeInformation.diff_common_keys(func_gen, instr_info.gen)

            # Generate kill map for given block.
            info.kill = NodeInformation.diff_common_keys(func_gen, info.gen)
 
    # Gets the blocks sorted in the order needed for the analysis.
    @abstractmethod
    def _get_sorted_blocks(self, func_block):
        pass

    # Computes the information specific to the iterative data flow.
    @abstractmethod
    def _compute_info(self, func_block_info, sorted_blocks):
        pass


class ReachingDefinitionsAnalysis(IterativeDataflowAnalysis):
    """
    Determines reaching definitions for each class.
    """

    def __init__(self):
        super(self.__class__, self).__init__(ReachingDefinitions)

    def _get_sorted_blocks(self, func_block):
        return func_block.get_sorted_blocks()

    def _compute_info(self, func_block_info, sorted_blocks):
        for block in sorted_blocks:
            info = func_block_info.get_block_info(block)

            # Calculate in: Union all predecessors out.
            for func_name, predecessor in block.predecessors.items():
                predecessor_info = func_block_info.get_block_info(predecessor)
                info.in_node = NodeInformation.union(predecessor_info.out_node, info.in_node)

            # Calculate out: gen UNION (in - kill)
            in_sub_kill = NodeInformation.sub(info.in_node, info.kill)
            info.out_node = NodeInformation.union(info.gen, in_sub_kill)

            # Calculate block information for all instructions in the block.
            prev_info = info.in_node
            for instr in block.get_instructions():
                instr_info = func_block_info.get_instruction_info(instr.lineno)
                instr_info.in_node = prev_info

                in_sub_kill = NodeInformation.sub(instr_info.in_node, instr_info.kill)
                instr_info.out_node = NodeInformation.union(instr_info.gen, in_sub_kill)
                prev_info = instr_info.out_node
