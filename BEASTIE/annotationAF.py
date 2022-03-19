#!/usr/bin/env python
# =========================================================================
# 2021 Xue Zou (xue.zou@duke.edu)
# =========================================================================
from collections import namedtuple
import csv
import gzip
import logging
import multiprocessing
import pandas as pd
from pkg_resources import resource_filename


ANNOTATION_ALGORITH = "parallel_join"  #'constant_memory'
MAX_WORKERS = 4


def annotateAF(ancestry, hetSNP, out_AF):
    ancestry_map = {
        "EUR": "EUR",
        "CEU": "EUR",
        "TSI": "EUR",
        "FIN": "EUR",
        "GBR": "EUR",
        "IBS": "EUR",
        "AFR": "AFR",
        "YRI": "AFR",
        "LWK": "AFR",
        "GWD": "AFR",
        "MSL": "AFR",
        "ESN": "AFR",
        "ASW": "AFR",
        "ACB": "AFR",
        "SAS": "SAS",
        "GIH": "SAS",
        "PJL": "SAS",
        "BEB": "SAS",
        "STU": "SAS",
        "ITU": "SAS",
        "EAS": "EAS",
        "CHB": "EAS",
        "JPT": "EAS",
        "CHS": "EAS",
        "CDX": "EAS",
        "KHV": "EAS",
        "AMR": "AMR",
        "MXL": "AMR",
        "PUR": "AMR",
        "CLM": "AMR",
        "PEL": "AMR",
    }

    ancestry_group = ancestry_map[ancestry]

    if ANNOTATION_ALGORITH == "parallel_join":
        annotateAFConstantMemoryParallel(ancestry_group, hetSNP, out_AF)
    elif ANNOTATION_ALGORITH == "constant_memory":
        AF_file = resource_filename("BEASTIE", "reference/AF/AF_1_22_trimmed2.csv.gz")
        annotateAFConstantMemory(ancestry_group, hetSNP, out_AF, AF_file)
    else:
        AF_file = resource_filename("BEASTIE", "reference/AF/AF_1_22_trimmed2.csv")
        annotateAFPandas(ancestry_group, hetSNP, out_AF, AF_file)

    logging.info("..... finish annotating AF for SNPs, file save at {0}".format(out_AF))


def annotateAFPandas(ancestry, hetSNP, out_AF, AF_file):
    logging.info("..... start reading 1000 Genome AF annotation file")
    AF = pd.read_csv(AF_file, header=0, sep=",", engine="c", na_filter=False)
    logging.info("..... finish reading 1000 Genome AF annotation file")
    data = pd.read_csv(hetSNP, sep="\t", header=0, index_col=False)
    if ancestry == "EUR":
        AF = AF[["chr", "pos", "rsid", "EUR_AF"]]
        AF = AF.rename(columns={"EUR_AF": "AF"})
    elif ancestry == "AFR":
        AF = AF[["chr", "pos", "rsid", "AFR_AF"]]
        AF = AF.rename(columns={"AFR_AF": "AF"})
    elif ancestry == "EAS":
        AF = AF[["chr", "pos", "rsid", "EAS_AF"]]
        AF = AF.rename(columns={"EAS_AF": "AF"})
    elif ancestry == "AMR":
        AF = AF[["chr", "pos", "rsid", "AMR_AF"]]
        AF = AF.rename(columns={"AMR_AF": "AF"})
    elif ancestry == "SAS":
        AF = AF[["chr", "pos", "rsid", "SAS_AF"]]
        AF = AF.rename(columns={"SAS_AF": "AF"})
    data_AF = pd.merge(data, AF, on=["chr", "pos"], how="left")
    data_AF = data_AF.drop_duplicates()
    data_AF.to_csv(out_AF, sep="\t")


def annotateCHRLines(hetSNP_lines, chr, ancestry, hetSNP_chr_index, hetSNP_pos_index):
    AF_filename = resource_filename("BEASTIE", f"reference/AF/AF_{chr}.csv.gz")
    with gzip.open(AF_filename, mode="rt", newline="") as AF_file:
        af_reader = csv.reader(AF_file, delimiter=",", dialect="unix")
        af_header = next(af_reader)

        af_chr_index = af_header.index("chr")
        af_pos_index = af_header.index("pos")
        af_af_col_index = af_header.index(f"{ancestry}_AF")
        af_rsid_col_index = af_header.index("rsid")

        af_rows_left = True

        af_row = next(af_reader)
        af_chr, af_pos = af_row[af_chr_index], int(af_row[af_pos_index])
        af_chr_n = int(af_chr.strip("chr"))

        output = []
        for row in hetSNP_lines:
            chr, pos = row[hetSNP_chr_index], int(row[hetSNP_pos_index])
            chr_n = int(chr.strip("chr"))

            while af_rows_left and (
                (chr_n > af_chr_n) or (chr_n == af_chr_n and pos > af_pos)
            ):
                try:
                    af_row = next(af_reader)
                    af_chr, af_pos = af_row[af_chr_index], int(af_row[af_pos_index])
                    af_chr_n = int(af_chr.strip("chr"))
                except StopIteration:
                    af_row = None
                    af_rows_left = False

            if af_row is not None and chr_n == af_chr_n and pos == af_pos:
                output.append(
                    row + [af_row[af_rsid_col_index], af_row[af_af_col_index]]
                )
            else:
                output.append(row + ["", ""])
    return output


def annotateAFConstantMemoryParallel(ancestry, hetSNP, out_AF):
    logging.info("..... start annotating AF with parallel constant memory join")

    with multiprocessing.Pool(MAX_WORKERS) as pool, open(
        hetSNP, newline=""
    ) as hetSNPfile, open(out_AF, "w", newline="") as outFile:
        hetSNP_reader = csv.reader(hetSNPfile, delimiter="\t", dialect="unix")
        hetSNP_header = next(hetSNP_reader)

        hetSNP_chr_index = hetSNP_header.index("chr")
        hetSNP_pos_index = hetSNP_header.index("pos")

        output_handles = []

        current_chr = None
        current_rows = None

        for row in hetSNP_reader:
            chr = row[hetSNP_chr_index]
            if chr != current_chr:
                if current_chr is not None:
                    output_handles.append(
                        pool.apply_async(
                            annotateCHRLines,
                            (
                                current_rows,
                                current_chr,
                                ancestry,
                                hetSNP_chr_index,
                                hetSNP_pos_index,
                            ),
                        )
                    )
                current_chr = chr
                current_rows = []
            current_rows.append(row)
        if current_rows is not None and len(current_rows) > 0:
            output_handles.append(
                pool.apply_async(
                    annotateCHRLines,
                    (
                        current_rows,
                        current_chr,
                        ancestry,
                        hetSNP_chr_index,
                        hetSNP_pos_index,
                    ),
                )
            )

        pool.close()

        out_writer = csv.writer(
            outFile, delimiter="\t", dialect="unix", quoting=csv.QUOTE_MINIMAL
        )
        out_writer.writerow(hetSNP_header + ["rsid", "AF"])

        for handle in output_handles:
            handle.wait()
            output = handle.get()
            out_writer.writerows(output)


def annotateAFConstantMemory(ancestry, hetSNP, out_AF, AF_file):
    logging.info("..... start annotating AF with constant memory join")

    with gzip.open(AF_file, mode="rt", newline="") as affile, open(
        hetSNP, newline=""
    ) as hetSNPfile, open(out_AF, "w", newline="") as outFile:
        af_reader = csv.reader(affile, delimiter=",", dialect="unix")
        hetSNP_reader = csv.reader(hetSNPfile, delimiter="\t", dialect="unix")

        af_header = next(af_reader)
        hetSNP_header = next(hetSNP_reader)

        hetSNP_chr_index = hetSNP_header.index("chr")
        hetSNP_pos_index = hetSNP_header.index("pos")

        af_chr_index = af_header.index("chr")
        af_pos_index = af_header.index("pos")
        af_af_col_index = af_header.index(f"{ancestry}_AF")
        af_rsid_col_index = af_header.index("rsid")

        af_rows_left = True

        af_row = next(af_reader)
        af_chr, af_pos = af_row[af_chr_index], int(af_row[af_pos_index])
        af_chr_n = int(af_chr.strip("chr"))

        rows_written = 0
        rows_read = 0

        out_writer = csv.writer(
            outFile, delimiter="\t", dialect="unix", quoting=csv.QUOTE_MINIMAL
        )
        out_writer.writerow(hetSNP_header + ["rsid", "AF"])

        for row in hetSNP_reader:
            chr, pos = row[hetSNP_chr_index], int(row[hetSNP_pos_index])
            chr_n = int(chr.strip("chr"))

            while af_rows_left and (
                (chr_n > af_chr_n) or (chr_n == af_chr_n and pos > af_pos)
            ):
                try:
                    af_row = next(af_reader)
                    af_chr, af_pos = af_row[af_chr_index], int(af_row[af_pos_index])
                    af_chr_n = int(af_chr.strip("chr"))
                    rows_read += 1
                except StopIteration:
                    af_row = None
                    af_rows_left = False

            if af_row is not None and chr_n == af_chr_n and pos == af_pos:
                out_writer.writerow(
                    row + [af_row[af_rsid_col_index], af_row[af_af_col_index]]
                )
            else:
                out_writer.writerow(row + ["", ""])
            rows_written += 1
    logging.info("..... end annotating AF")