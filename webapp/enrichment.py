import cPickle
import sys
from collections import defaultdict
import sqlite3 as sql
from decimal import Decimal
import scipy.stats as stats
from scipy.misc import comb
import copy
import networkx as nx


def FDR_per_p_val(fisher_tests):
    """Returns a dictionary with an FDR per possible p-value.
    The input is a dictionary:
    fisher_tests['category']: [m, M, n, N]

    m = # genes of type A in list
    M = # all genes in list
    n = # genes of type A in entire population
    N = # all genes in population
    
    """

    categories = fisher_tests.keys()

    #calculate p-value for each of the categories
    p_value_per_category = {}

    cat_per_p_val = defaultdict(list)
    for cat in categories:
        p_value_per_category[cat] = hypergeom_p_plus(*fisher_tests[cat])        #hypergeometric test per category
##        p_value_per_category[cat] =  eval(str(p_value_per_category[cat]))   #there is weird behavior with long floating points 1 = 0.999999999999999999999
        cat_per_p_val[p_value_per_category[cat]].append(cat)


    #assume the p-values are the thresholds (alpha) and calculate the FDR for the p-value
    fdr_per_p_value = {}
    p_values = list(set(p_value_per_category.values())) #unique set of p-values so we are not iterating through distributions for the same alpha


    for p_val in p_values:
        alpha = p_val   #set alpha cutoff to p_value
        #calculate the expectation of number of false discoveries NFD as the sum of all probabilities that are
        #more extreme than m and less than alpha in all categories
        nfd = 0
        for cat in categories:
            m, M, n, N = fisher_tests[cat]
            prob_test = 0
            for a in range(min(M, n), -1, -1):  #sum all probabilities till alpha is reached
                p = hypergeom_pmf(a,M,n,N)
                if prob_test + p <= alpha:
                    prob_test += p
                else:
                    break
            nfd += prob_test    # add the probability < alpha sum for each category to nfd

        #for all p_values check how many are less than the current p_value/alpha.
        #note there will always be at least 1
        r = 0   #this is the number of positives
        for p_val2 in p_value_per_category.values():    #iterate through all tests
            if p_val2 <= alpha:
                r += 1
        
        fdr = nfd / r
        fdr = min(fdr, 1.0)
        fdr_per_p_value[alpha] = fdr

    fdr_per_cat = {}
    for p_val in fdr_per_p_value:
        for cat in cat_per_p_val[p_val]:
            fdr_per_cat[cat] = fdr_per_p_value[p_val]

    pvalues = [(p_value_per_category[cat], fdr_per_cat[cat], cat, fisher_tests[cat][0], fisher_tests[cat][1], fisher_tests[cat][2], fisher_tests[cat][3], set()) for cat in fdr_per_cat]
            
    return pvalues

def contingency_tables(annotations=defaultdict(set), input=set(), min_genes=2, background=set()):
    fisher_tests = {}

    #annotations is a annotation->set(genes) default dictionary
    #remove genes from input that dont have any annotation
    input = copy.deepcopy(input)
    annotations = copy.deepcopy(annotations)
    all_genes = set()
    map(lambda x: all_genes.update(x), annotations.values())
    #all genes must belong in background
    if background:
        all_genes &= background
    input &= all_genes

    #filter step
    #remove all annotations that do not have a single input gene
    annots_to_remove = []
    for annot in annotations:
        annotations[annot] &= all_genes
        fisher_tests[annot] = [0, len(input), len(annotations[annot]), len(all_genes)]
        if not (input & annotations[annot]):
            annots_to_remove.append(annot)
    for annot in annots_to_remove:
        del annotations[annot]
    
    p_values = []
    for annot in annotations:
        m_genes = annotations[annot].intersection(input)
        m = len(m_genes)     # input genes with annotation
        if not m >= min_genes:
            continue
        M = len(input)                                      # total input genes
        n = len(annotations[annot])                         # background genes with annotation
        N = len(all_genes)                                  # total background

        fisher_tests[annot][0] = m

    del input
    del annotations
    return fisher_tests   

def fishers(annotations=defaultdict(set), input=set(), alpha=1, min_genes=2, background=set()):
    """This is the basic fisher's exact test
    """

    #annotations is a annotation->set(genes) default dictionary
    #remove genes from input that dont have any annotation
    input = copy.deepcopy(input)
    annotations = copy.deepcopy(annotations)
    num_annotations = len(annotations)
    all_genes = set()
    map(lambda x: all_genes.update(x), annotations.values())
    #all genes must belong in background
    if background:
        all_genes &= background
    input &= all_genes

    #filter step
    #remove all annotations that do not have a single input gene
    annots_to_remove = []
    for annot in annotations:
        annotations[annot] &= all_genes
        if not (input & annotations[annot]):
            annots_to_remove.append(annot)
    for annot in annots_to_remove:
        del annotations[annot]
    
    p_values = []
    for annot in annotations:
        #print annot
        m_genes = annotations[annot].intersection(input)
        m = len(m_genes)     # input genes with annotation
        if not m >= min_genes:
            continue
        M = len(input)                                      # total input genes
        n = len(annotations[annot])                         # background genes with annotation
        N = len(all_genes)                                  # total background
        p_value = hypergeom_p_plus(m, M, n, N, alpha=alpha)
        if p_value == 1.0:
            continue
        #apply bonferroni correction
        bonferroni_p_value = p_value * num_annotations
        benjamini_p_value = p_value * num_annotations
        p_values.append({'P-Value': p_value,
                         'Bonferroni P-Value': bonferroni_p_value,
                         'Benjamini P-Value': benjamini_p_value,
                         'Annotation': annot,
                         'm': m,
                         'M': M,
                         'n': n,
                         'N': N,
                         'Input Annotated': list(m_genes)})

    p_values.sort(key=lambda x: x['P-Value'])
    #update benjamini correction
    for i, p_val in enumerate(p_values):
        p_val['Benjamini P-Value'] /= i+1

    del input
    del annotations
    return p_values                

def remove_all_seen_genes(annotations=defaultdict(set), input=set(), alpha=1, min_genes=2, background=set()):
    """This is the Elim algorithm
    """
    
    #annotations is a annotation->set(genes) default dictionary

    input = copy.deepcopy(input)
    annotations = copy.deepcopy(annotations)
    
    #remove genes from input that dont have any annotation
    all_genes = set()
    map(lambda x: all_genes.update(x), annotations.values())
    #all genes must belong in background
    if background:
        all_genes &= background
    input &= all_genes

    #filter step
    #remove all annotations that do not have a single input gene
    correction = len(annotations)
    annots_to_remove = []
    for annot in annotations:
        annotations[annot] &= all_genes
        if not (input & annotations[annot]):
            annots_to_remove.append(annot)
    for annot in annots_to_remove:
        del annotations[annot]
        
    top_annotations = []
    accounted_genes = set()
    #iteratively add to top annotations the best annotation to explain all genes
    while input:
        #calculate p-value for all annotations if there is at least one input gene
        p_values = []
        for annot in annotations:
            m_genes = annotations[annot].intersection(input)
            m = len(m_genes)     # input genes with annotation
            if not m >= min_genes:
                continue            
            M = len(input)                                      # total input genes
            n = len(annotations[annot])                         # background genes with annotation
            N = len(all_genes)                                  # total background
            p_value = hypergeom_p_plus(m, M, n, N, alpha=alpha)
            if p_value == 1.0:
                continue
            #apply bonferroni correction
            bonferroni_p_value = p_value * correction
            p_values.append((p_value, bonferroni_p_value, annot, m, M, n, N, m_genes))

        # if no annotation has a good p-value, then break
        if not p_values:
            break

        # pick best annotation
        p_values.sort()

        #add best to top_annotations
        top_annotations.append(p_values[0])

        #remove the input genes that have been accounted for from input and background
        accounted_genes = accounted_genes.union(input & annotations[p_values[0][2]])
        input -= accounted_genes
        all_genes -= accounted_genes
        #also remove all empty annotations
        annots_to_remove = []
        for annot in annotations:
            annotations[annot] -= accounted_genes
            if not annotations[annot]:
                annots_to_remove.append(annot)

        for annot in annots_to_remove:
            del annotations[annot]            


    del input
    del annotations
    return top_annotations        
    
def remove_subset_annotations(annotations=defaultdict(set), input=set(), alpha=1, min_genes=2, background=set()):
    """This algorithm removes annotations if they only contain seen genes, but does not remove any genes
    """
    
    #annotations is a annotation->set(genes) default dictionary

    input = copy.deepcopy(input)
    annotations = copy.deepcopy(annotations)
    
    #remove genes from input that dont have any annotation
    all_genes = set()
    map(lambda x: all_genes.update(x), annotations.values())
    #all genes must belong in background
    if background:
        all_genes &= background
    input &= all_genes

    #filter step
    #remove all annotations that do not have a single input gene
    correction = len(annotations)
    annots_to_remove = []
    for annot in annotations:
        annotations[annot] &= all_genes
        if not (input & annotations[annot]):
            annots_to_remove.append(annot)
    for annot in annots_to_remove:
        del annotations[annot]

    top_annotations = []
    accounted_genes = set()
    #iteratively add to top annotations the best annotation to explain all genes
    while input:
        #calculate p-value for all annotations if there is at least one input gene
        p_values = []
        for annot in annotations:
            m_genes = annotations[annot].intersection(input)
            m = len(m_genes)     # input genes with annotation
            if not m >= min_genes:
                continue
            M = len(input)                                      # total input genes
            n = len(annotations[annot])                         # background genes with annotation
            N = len(all_genes)                                  # total background
            p_value = hypergeom_p_plus(m, M, n, N, alpha=alpha)
            if p_value == 1.0:
                continue
            #apply bonferroni correction
            bonferroni_p_value = p_value * correction
            p_values.append((p_value, bonferroni_p_value, annot, m, M, n, N, m_genes))

        # if no annotation has a good p-value, then break
        if not p_values:
            break

        # pick best annotation
        p_values.sort()

        #add best to top_annotations
        top_annotations.append(p_values[0])

        #Do not remove any genes
        accounted_genes = accounted_genes.union(input & annotations[p_values[0][2]])
##        input -= accounted_genes
        #delete annotations if it contains only seen input genes
        annots_to_remove = []
        for annot in annotations:
            if not ((annotations[annot]-accounted_genes) & input):
                annots_to_remove.append(annot)

        for annot in annots_to_remove:
            del annotations[annot]  

    del input
    del annotations
    return top_annotations

def remove_subset_simple(p_values, min_genes=2):
    final_set = [p_values[0]]
    seen_genes = set() | p_values[0][7]
    for data in p_values[1:]:
        if len(data[7] - seen_genes) >= min_genes:
            final_set.append(data)
            seen_genes |= data[7]

    return final_set            
        

def xor(*set_list):
    return set.union(*set_list) - set.intersection(*set_list)

def union(*set_list):
    return set.union(*set_list)

def intersection(*set_list):
    return set.intersection(*set_list)

def single_set_operation_annotations(annotations=defaultdict(set), input=set(), operation=set.union, alpha=1, break_at_worse=0, min_genes=2, background=set()):
    """This algorithm tries to find combinations of annotations that returns the best p_value
    operations are performed on lists of sets. operations must be symmetric
    """
    
    #annotations is a annotation->set(genes) default dictionary

    input = copy.deepcopy(input)
    annotations = copy.deepcopy(annotations)
    
    #remove genes from input that dont have any annotation
    all_genes = set()
    map(lambda x: all_genes.update(x), annotations.values())
    input &= all_genes

    #filter step
    #remove all annotations that do not have a single input gene
    correction = len(annotations)
    annots_to_remove = []
    for annot in annotations:
        annotations[annot] &= all_genes
        if not (input & annotations[annot]):
            annots_to_remove.append(annot)
    for annot in annots_to_remove:
        del annotations[annot]


    combo_annotations = []

    ignore_annots = []
    #find first pair of combo
    p_values  = []
    for annot1 in annotations:
        for annot2 in annotations:
            if annot1 >= annot2:
                continue
            n_genes = operation(*[annotations[annot1], annotations[annot2]])
            m_genes = n_genes.intersection(input)
            m = len(m_genes)     # input genes with annotation
            if not m >= min_genes:
                continue
            M = len(input)                                      # total input genes
            n = len(n_genes)                                    # background genes with combo_annotation
            N = len(all_genes)                                  # total background
            p_value = hypergeom_p_plus(m, M, n, N, alpha=alpha)
            if p_value == 1.0:
                continue
            #apply bonferroni correction
            bonferroni_p_value = p_value * correction
            p_values.append([p_value, bonferroni_p_value, (annot1, annot2), m, M, n, N, m_genes])

    if not p_values:
        return combo_annotations

    p_values.sort()
    top2_annots = p_values[0][2]
    #start it off by adding best p_value
    combo_annotations.append(p_values[0])
    combo_annotations.append(p_values[0])
    combo_annotations[0][2] = top2_annots[0]
    combo_annotations[0] = tuple(combo_annotations[0])
    combo_annotations[1][2] = top2_annots[1]
    combo_annotations[1] = tuple(combo_annotations[1])
    
    #delete best annotations - ignore next time
    ignore_annots.append(combo_annotations[0][2])
    ignore_annots.append(combo_annotations[1][2])  

    #iteratively add 1 new annotation to combo_annotation if p_value is improved or don't get worse
    while 1:
        #at each iteration combine
        added = 0
        p_values = []
        for annot in annotations:
            if annot in ignore_annots:
                continue
            temp_combo_annots = [tup[2] for tup in combo_annotations] + [annot]
            #calculate p_value using set operation
            n_genes = operation(*[annotations[a] for a in temp_combo_annots])
            m_genes = n_genes.intersection(input)
            m = len(m_genes)     # input genes with annotation
            if not abs(m-len(combo_annotations[-1][7])) >= min_genes:
                continue
            M = len(input)                                      # total input genes
            n = len(n_genes)                                    # background genes with combo_annotation
            N = len(all_genes)                                  # total background
            p_value = hypergeom_p_plus(m, M, n, N, alpha=alpha)
            if p_value == 1.0:
                continue
            #apply bonferroni correction
            bonferroni_p_value = p_value * correction
            p_values.append((p_value, bonferroni_p_value, annot, m, M, n, N, m_genes))

        # if no annotation has a good p-value, then break
        if not p_values:
            break

        # pick best annotation
        p_values.sort()
        top_p_value = p_values[0][0]
        top_annotation = p_values[0][2]

        #break if you only want to continue while p_value improves
        if break_at_worse and top_p_value > combo_annotations[-1][0]:
            break

        #add best annotation to combo        
        combo_annotations.append(p_values[0])

        #delete annotation to ignore in next iteration
        ignore_annots.append(top_annotation)
   

    del input
    del annotations
    return combo_annotations

def set_operation_annotations(annotations=defaultdict(set), input=set(), operation=set.intersection, alpha=1, next_at_worse=0):
    pass


   
def p_values_filter(p_values, column=0, threshold=1.0, below=True):
    filter_values = []
    for data in p_values:
        if below:
            if data[column] <= threshold:
                filter_values.append(data)
        else:
            if data[column] >= threshold:
                filter_values.append(data)

    return filter_values

def hypergeom_pmf(m,M,n,N):
    """Returns probability mass function value for hypergeometric distribution with:
    m = # genes of type A in list
    M = # all genes in list
    n = # genes of type A in entire population
    N = # all genes in population

    """

    return float(Decimal(comb(n, m, exact=1) * comb(N-n, M-m, exact=1)) / Decimal(comb(N, M, exact=1)))

def hypergeom_p_plus(m, M, n, N, alpha=1.0, midP=False):
    """Returns p value for hypergeometric distribution with:
    m = # genes of type A in list
    M = # all genes in list
    n = # genes of type A in entire population
    N = # all genes in population

    """


    p_plus = 0
    start = m
    stop = min(M,n)
    assert start <= stop
    if midP and start + 1 <= stop:
        start += 1

##    for a in range(start, stop+1):
    for a in range(stop, start-1, -1):
##        p_plus += float(stats.hypergeom.pmf(a, N, n, M))
        val = hypergeom_pmf(a,M,n,N)
        p_plus += val
        if p_plus > alpha:
            return 1.0

    if midP:
##        p_plus += 0.5*float(stats.hypergeom.pmf(m, N, n, M))
        p_plus += 0.5*hypergeom_pmf(m,M,n,N)
        if p_plus > alpha:
            return 1.0

    return p_plus

def hypergeom_p_minus(m, M, n, N, alpha=1.0, midP=False):
    """Returns p value for hypergeometric distribution with:
    m = # genes of type A in list
    M = # all genes in list
    n = # genes of type A in entire population
    N = # all genes in population

    """


    p_minus = 0
    start = 0
    stop = m
    
    if midP and stop - 1 <= start:
        stop += 1

##    for a in range(start, stop+1):
    for a in range(start, stop+1, 1):
##        p_minus += float(stats.hypergeom.pmf(a, N, n, M))
        val = hypergeom_pmf(a,M,n,N)
        p_minus += val
        if p_minus > alpha:
            return 1.0

    if midP:
##        p_minus += 0.5*float(stats.hypergeom.pmf(m, N, n, M))
        p_minus += 0.5*hypergeom_pmf(m,M,n,N)
        if p_minus > alpha:
            return 1.0

    return p_minus


if __name__ == "__main__":
    pass
  
