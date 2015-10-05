#!/usr/bin/env python

from glob import glob
import argparse
import os
import subprocess

word_limit = {'PRL': 3500,
              'PRA-RC': 3500,
              'PRB-RC': 3500,
              'PRC-RC': 4500,
              'PRD-RC': 4000,
              'PRE-RC': 3500,
              'PRApplied': 3500,
              'PRST-PER': 3500}


def is_first_line(line):
    if line.strip() == '':
        return False
    if '%' in line:
        return False
    return True


def count_main_text_words_detex(detex_lines, tex_lines):
    # remove images and empty lines
    detex_lines = [line for line in detex_lines if len(line.strip()) > 0]
    detex_lines = [line for line in detex_lines if '<Picture' not in line]

    title_line_no, = [i for i, line in enumerate(tex_lines) if
                      '\maketitle' in line]
    first_line_no = title_line_no + 1
    while not is_first_line(tex_lines[first_line_no]):
        first_line_no += 1
    first_line = tex_lines[first_line_no]

    detex_first_line_no = 0
    for line in detex_lines:
        if line.strip() == first_line.strip():
            break
        detex_first_line_no += 1

    main_text = detex_lines[detex_first_line_no:]

    main_text = [line.replace('-', ' ') for line in
                 main_text]  # hyphenated words count as two words
    lines_words = [line.split() for line in main_text]
    words = [word for words in lines_words for word in words]

    # words_file = open('words', 'w')
    # words_file.writelines([word+'\n' for word in words])
    # words_file.close()

    main_text_words = len(words)
    return main_text_words


def count_main_text_words_wordcount(tex_lines, args):
    """
    Count words in main text following method described at
    
    http://journals.aps.org/authors/length-guide-faq
    """
    mod_tex_lines = tex_lines[:]

    # Commenting out the \maketitle command
    mod_tex_lines = [line.replace(r'\maketitle', r'%\maketitle') for line in
                     mod_tex_lines]

    # Using the 'nofootinbib' option
    mod_tex_lines = [
        line.replace(r'\documentclass[', r'\documentclass[nofootbib, ')
        for line in mod_tex_lines]
    # Putting an \end{document} before the bibliography
    bib_index = [i for (i, line) in enumerate(mod_tex_lines) if
                 r'\bibliography{' in line]
    if bib_index:
        mod_tex_lines.insert(bib_index[0], r'\end{document}' + '\n')

    # Putting an \end{document} before the acknowledgments/acknowledgements in environment \acknowledgments{...}
    ack_index = [i for (i, line) in enumerate(mod_tex_lines) if
                 r'\acknowle' in line]
    if ack_index:
        mod_tex_lines.insert(ack_index[0], r'\end{document}' + '\n')


    # Comment out any display equations and acknowledgments
    filterenvs = ['equation', 'eqnarray', 'align', 'displaymath',
                  'acknowledgments',
                  'acknowledgements', 'abstract', 'thebibliography']
    filtered_lines = []
    while mod_tex_lines:
        line = mod_tex_lines.pop(0)
        for env in filterenvs:
            if r'\begin{%s' % env in line:
                while mod_tex_lines and not r'\end{%s}' % env in line:
                    line = '% ' + line
                    filtered_lines.append(line)
                    line = mod_tex_lines.pop(0)
                line = '% ' + line
                filtered_lines.append(line)
                line = mod_tex_lines.pop(0)  # comment out the \end too
        filtered_lines.append(line)
    mod_tex_lines = filtered_lines

    # FIXME - Commenting out the rows (but not the caption) of any tables

    tmp_tex_file = open('tmp_tex_file.tex', 'w')
    tmp_tex_file.writelines(line for line in mod_tex_lines)
    tmp_tex_file.close()

    os.system('%s tmp_tex_file > /dev/null 2>&1' % args.latex)
    os.system('bibtex tmp_tex_file > /dev/null 2>&1')
    os.system('%s tmp_tex_file > /dev/null 2>&1' % args.latex)
    os.system('%s tmp_tex_file > /dev/null 2>&1' % args.latex)
    os.system(
        r'echo tmp_tex_file.tex | %s wordcount.tex > /dev/null 2>&1' % args.latex)
    wordcount_log = open('wordcount.log').readlines()

    rm_files = glob('wordcount*') + glob('tmp_tex_file*')
    for file in rm_files:
        os.unlink(file)

    wordcount = len([line for line in wordcount_log if
                     '3.08633' in line or '3.08635' in line])
    return wordcount


def find_equation_lines(tex_lines):
    return [i for (i, line) in enumerate(tex_lines) if
            (r'\begin{equation' in line or
             r'\begin{eqnarray' in line or
             r'\begin{align' in line or
             r'\begin{displaymath' in line)]


def count_equation_words(lines, start_line):
    count = 1
    array = False
    array_lines = 0
    two_column = '*' in lines[start_line]
    if two_column:
        eqn_words_per_line = 32
    else:
        eqn_words_per_line = 16

    for line in lines[start_line + 1:]:
        if (r'\end{equation' in line or
                    r'\end{eqnarray' in line or
                    r'\end{align' in line or
                    r'\end{displaymath' in line):
            break
        if r'\\' in line:
            if not array:
                count += 1
            else:
                array_lines += 1
        if r'\begin{array}' in line:
            array = True
            array_lines = 0
        if r'\end{array}' in line:
            array = False

    if array_lines != 0:
        count *= array_lines

    return count * eqn_words_per_line


def count_equations_words(tex_lines):
    eqn_line_nos = find_equation_lines(tex_lines)
    eqn_words = [count_equation_words(tex_lines, eqn_line_no) for eqn_line_no in
                 eqn_line_nos]
    print('Equations: %r' % eqn_words)
    return sum(eqn_words)


def find_table_lines(tex_lines):
    return [i for (i, line) in enumerate(tex_lines) if r'\begin{tabl' in line]


def count_table_words(tex_lines, table_line):
    two_column = 'table*' in tex_lines[table_line]
    count = 1
    for line in tex_lines[table_line:]:
        if r'\end{table' in line:
            break
        if r'\\' in line:
            count += 1
    if two_column:
        print(u'Two-column table with {0:d} lines'.format(count))
        return int(13. * count + 26.)
    else:
        print(u'Single-column table with {0:d} lines'.format(count))
        return int(6.5 * count + 13.)


def count_tables_words(tex_lines):
    table_lines = find_table_lines(tex_lines)
    table_words = [count_table_words(tex_lines, table_line) for table_line in
                   table_lines]
    print(u'Tables: {0!r:s}'.format(table_words))
    return sum(table_words)


def count_figures_words(detex_lines, tex_lines, opts):
    if opts.var is None:
        tex_vars = {}
    else:
        tex_vars = dict(opts.var)

    fig_lines = [line for line in detex_lines if '<Picture' in line]
    fig_words = []
    # figs = {}

    pathline = [line for line in tex_lines if 'graphicspath' in line]
    if pathline:
        fig_path = pathline[0].split('{')[-1].split('}')[0]
    else:
        fig_path = ''

    for fig_i, fig_line in enumerate(fig_lines):
        filename = fig_line.strip()[1:-1].split()[1]
        this_fig_lines = [(i, line) for i, line in enumerate(tex_lines) if
                          filename in line and
                          ('input' in line or 'includegraphics' in line)]
        (inc_fig_line_no, inc_fig_line), = this_fig_lines
        fig_line_no = inc_fig_line_no
        while r'\begin{figure' not in tex_lines[fig_line_no]:
            fig_line_no -= 1
        two_column = 'figure*' in tex_lines[fig_line_no]

        subfig = 'subfloat' in tex_lines[inc_fig_line_no]
        newline = r'\\' in tex_lines[inc_fig_line_no]

        # print filename, tex_lines[inc_fig_line_no], tex_lines[fig_line_no]

        filename = fig_path + filename

        for key in tex_vars.keys():
            if key in filename:
                filename = filename.replace(key, tex_vars[key])

        for ext in ['', '.pdf', '.eps', '.png']:
            if len(glob(filename + ext)) == 1:
                break
        else:
            raise IOError('missing picture file %s' % filename)
        filename += ext

        if opts.figs == 'identify':
            identify = subprocess.Popen(['identify', filename],
                                        stdout=subprocess.PIPE)
            out, err = identify.communicate()
            fields = out.split()
            width, height = fields[2].split('x')
            width = float(width)
            height = float(height)
        elif opts.figs == 'gs':
            img_f = open(filename, 'r')
            gs = subprocess.Popen(
                ['gs', '-q', '-dSAFER', '-dBATCH', '-sDEVICE=bbox', '-'],
                stdin=img_f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            err = gs.communicate()[1]
            img_f.close()
            bbox = err.split('\n')[0].split()
            width = float(bbox[3])
            height = float(bbox[4])
        else:
            raise ValueError('Unknown figure method "%s"' % opts.figs)

        # if fig_line_no not in figs:
        #    figs[fig_line_no] = (fig_i, two_column, [(width, height, newline, filename)])
        # else:
        #    figs[fig_line_no][2].append((width, height, newline, filename))

        aspect = float(width / height)

        if two_column:
            words_equiv = 300. / (0.5 * aspect) + 40.
        else:
            words_equiv = 150. / aspect + 20.

        print('Figure %d:   %6d words (%.0fx%.0f aspect %.2f, %s)'
              % (fig_i + 1, int(words_equiv), width, height, aspect, filename))
        fig_words.append(words_equiv)

    return int(sum(fig_words) * opts.scale_figs)


def count_chars_abstract(tex_lines):
    # print(tex_lines)
    abs_begin_line, = [i for (i, line) in enumerate(tex_lines) if
                       r'\begin{abstract}' in line]
    abs_end_line, = [i for (i, line) in enumerate(tex_lines) if
                     r'\end{abstract}' in line]
    abstract_lines = tex_lines[abs_begin_line + 1:abs_end_line]
    abstract_lines = [line for line in abstract_lines
                      if not line.startswith('%')]
    abstract = ''.join(abstract_lines)
    print(abstract)
    return len(abstract)


def process_tex(tex_file, args):
    print(u'Processing TeX file: {0:s}\n'.format(tex_file))
    detex = subprocess.Popen(['detex', '-e', args.env, tex_file],
                             stdout=subprocess.PIPE)
    detex_out = detex.communicate()[0]
    detex_lines = detex_out.strip().split('\n')

    with open(tex_file) as f:
        tex_lines = f.readlines()

    abstract_chars = count_chars_abstract(tex_lines)
    print(u'Abstract:    {0:6d} chars (max 600)'.format(abstract_chars))

    print('method = ' + args.method)
    if args.method == 'detex':
        main_text_words = count_main_text_words_detex(detex_lines, tex_lines)
    elif args.method == 'wordcount':
        main_text_words = count_main_text_words_wordcount(tex_lines, args)
    else:
        raise ValueError('Unsupported method %s' % args.method)
    print(u'Main text:      {0:6d} words'.format(main_text_words))

    eqn_words = count_equations_words(tex_lines)
    print(u'Displayed Math: {0:6d} words'.format(eqn_words))

    fig_words = count_figures_words(detex_lines, tex_lines, args)
    print(u'Figures:        {0:6d} words'.format(fig_words))

    table_words = count_tables_words(tex_lines)
    print(u'Tables:         {0:6d} words'.format(table_words))

    total_words = (main_text_words + eqn_words + fig_words + table_words)

    print(u'Main text:      {0:6d} words'.format(main_text_words))
    print(u'Displayed Math: {0:6d} words'.format(eqn_words))
    print(u'Figures:        {0:6d} words'.format(fig_words))
    print(u'Tables:         {0:6d} words'.format(table_words))
    print(u'TOTAL:          {0:6d} words'.format(total_words))

    wl = word_limit[args.journal]
    if total_words > wl:
        over_under = 'OVER'
    else:
        over_under = 'UNDER'
    print(u'Manuscript {0:s} is currently {1:d} words ({2:.0f}%) {3:s} limit of {4:d} words '
          u'for journal {0:s}'.format(tex_file, abs(total_words - wl),
                                      float(total_words - wl) / wl * 100., over_under,
                                      wl, args.journal))


# _____________________________________________________________________________
# Parse the command line arguments
#
parser = argparse.ArgumentParser(usage='%(prog)s [options] tex-files',
                                 description="""Count length of an APS manuscript formatted in LaTeX, following
                        guidelines described at http://journals.aps.org/authors/length-guide""")

parser.add_argument('tex_files', metavar='file1.tex,file2.tex,...', nargs='+',
                    # type=argparse.FileType('r'),
                    help='The  name of tex files')
parser.add_argument('-v', '--var', metavar='key value', nargs=2,
                    action='append',
                    help='Define TeX variables e.g. to specify location of figure files.')
parser.add_argument('-e', '--env', metavar='env1,env2,...',
                    help='Comma-separated list of LaTeX environments to ignore.',
                    default='abstract,acknowledgements,displaymath,equation,eqnarray,thebibliography')
parser.add_argument('-m', '--method', metavar='(detex | wordcount)',
                    default='wordcount',
                    help='''Tool to use to count words in main text. Default is wordcount.
                    detex is also supported (but tends to underestimate word count).''')
parser.add_argument('-f', '--figs', metavar='(identify | gs)',
                    help='''Tool to use to extract bounding box from figure.
                    Default is gs, ImageMagick identify also supported. gs works with eps and pdf
                    images, while identify is a better choice for png images.''',
                    default='gs')
parser.add_argument('--scale-figs', type=float, default=1.1,
                    help='Scale estimate of figure word counts by factor, default 1.1 (10%)')
parser.add_argument('-j', '--journal', metavar='PRL', default='PRL',
                    help='Journal abbreviation (e.g. PRL, PRB-RC)')
parser.add_argument('-l', '--latex', default='pdflatex',
                    help='Latex executable. Default is "pdflatex".')

args = parser.parse_args()
orig_eps_pdf_files = glob('*-eps-converted-to.pdf')

tex_files = args.tex_files
del args.tex_files

for tex_file in tex_files:
    print(tex_file)
    process_tex(tex_file, args)

for eps_pdf_file in glob('*-eps-converted-to.pdf'):
    if eps_pdf_file not in orig_eps_pdf_files:
        os.remove(delname)
