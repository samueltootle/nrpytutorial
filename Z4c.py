from traceback import print_exc
import grid
import os
from sympy import sympify
from sympy import Eq, Ne, Piecewise, Rational
from sympy import pi
from sympy.functions.elementary.miscellaneous import cbrt, Max, sqrt

import NRPy_param_funcs as par
import indexedexp as ixp
from cactusthorn import CactusThorn, loop
from outputC import lhrh, outCparams

import safewrite
#safewrite.nochange = True
#safewrite.verbose = True

outCparams.CSE_enable = "True"

# "CCTK_REAL" or "CCTK_REALVEC"
par.set_parval_from_str("PRECISION", "CCTK_REALVEC")

# Current options are Carpet and CarpetX
grid.ET_driver = "CarpetX"

thorn = CactusThorn("CarpetXNRPy", "Z4cNRPy")

fd_order = thorn.declare_param('fd_order', default=4, vmin=2, vmax=8, doc="Finite differencing order")

fd_order = 4
par.set_parval_from_str("finite_difference::FD_CENTDERIVS_ORDER", fd_order)

centering='VVV'

# EVOL: evolved grid functions (possibly multiple time levels)
# AUXEVOL: needed for evolution, can be freed after evaluating rhs (1 time level)
# AUX: e.g. RHS (1 time level)
# TILE_TMP: not actually a grid function, only temporary tile
# SCALAR_TMP: not actually a grid function, only a double
import sympy as sp

# Generic helpers

def sum1(expr):
    result = sympify(0)
    for i in range(3):
        result += expr(i)
    return result

def sum2(expr):
    result = sympify(0)
    for i in range(3):
        for j in range(3):
            result += expr(i, j)
    return result

def sum2_symm(expr):
    result = sympify(0)
    for i in range(3):
        for j in range(i+1):
            result += (1 if i==j else 2) * expr(i, j)
    return result

def tensor1(expr):
    return [expr(i) for i in range(3)]

def tensor2(expr):
    return [[expr(i, j) for j in range(3)] for i in range(3)]

def tensor3(expr):
    return [[[expr(i, j, k) for k in range(3)] for j in range(3)] for i in range(3)]

def tensor4(expr):
    return [[[[expr(i, j, k, l) for l in range(3)] for k in range(3)] for j in range(3)] for i in range(3)]

# TODO: Specify names `gxx` etc.
def ixnam(i):
    return ["x", "y", "z"][i]

def namefun(symbol, index, shape, prefix):
    symbol = prefix
    result = [sp.Symbol(symbol + ''.join(ixnam(n) for n in index + [i]))
            if symbol else sp.sympify(0) for i in range(shape[0])]
    return result

set_Theta_zero = thorn.declare_param('set_Theta_zero', default=False, doc="set_Theta_zero")
kappa1 = thorn.declare_param('kappa1', default=0.02, doc="kappa1")
kappa2 = thorn.declare_param('kappa2', default=0.0, doc="kappa2")
f_mu_L = thorn.declare_param('f_mu_L', default=2.0, doc="f_mu_L")
f_mu_S = thorn.declare_param('f_mu_S', default=1.0, doc="f_mu_S")
eta = thorn.declare_param('eta', default=2.0, doc="eta")
alphaG_floor = thorn.declare_param('alphaG_floor', default=1.0e-10, vmin=0.0, doc="alphaG_floor")
chi_floor = thorn.declare_param('chi_floor', default=1.0e-10, vmin=0.0, doc="chi_floor")
eps_diss = thorn.declare_param('eps_diss', default=0.2, vmin=0.0, vmax=1.0, doc="eps_diss")


import safewrite

from sugar import *
decl_indexes()
set_coords("x","y","z")

gfparams(gf_type="EXTERNAL",symmetries="sym01",centering=centering,external_module="ADMBase",namefun=name_xyz)
#gfdecl("g","k",[la,lb],"alp","dtalp",[],"beta","dtbeta",[ua])

gflatex(r"g_{i j} k_{i j} alp dtalp beta^i dtbeta^i")
gfparams(gf_type="EXTERNAL",symmetries="sym01",centering=centering,external_module="TmunuBase",namefun=name_xyz)
gfdecl("eTtt",[],"eTt",[la],"eT",[la,lb])

gfparams(gf_type="EVOL",symmetries="sym01",centering=centering)
gfdecl("chi",[],"gammatilde",[la,lb],"Khat",[],"Atilde",[la,lb],"Gammatilde",[ua],"Theta","alphaG",[],"betaG",[ua])

gfparams(gf_type="AUX",symmetries="sym01",centering=centering)
gfdecl("rhs_chi",[],"rhs_gammatilde",[la,lb],"rhs_Khat",[],"rhs_Atilde",[la,lb], \
    "rhs_Gammatilde",[ua],"rhs_Theta","rhs_alphaG",[], "rhs_betaG", [ua],"ZetatildeC",[ua],\
    "HC",[],"MtildeC",[ua],"allC",[])
# Derivatives as calculated by NRPy

#chi_dD = ixp.declarerank1("chi_dD")
gfparams(gf_type="DERIV")
gfdecl("chi_d",[li],"chi_d",[li,lj],"chi_dup",[li],"chi_ddn",[li])

#chi_dDD = ixp.declarerank2("chi_dDD", "sym01")
#chi_dupD = ixp.declarerank1("chi_dupD")
#chi_ddnD = ixp.declarerank1("chi_ddnD")
chi_dKOD = ixp.declarerank1("chi_dKOD")

gammatildeDD_dD = ixp.declarerank3("gammatildeDD_dD", "sym01")
gammatildeDD_dDD = ixp.declarerank4("gammatildeDD_dDD", "sym01_sym23")
gammatildeDD_dKOD = ixp.declarerank3("gammatildeDD_dKOD", "sym01")
Khat_dD = ixp.declarerank1("Khat_dD")
Khat_dKOD = ixp.declarerank1("Khat_dKOD")
AtildeDD_dD = ixp.declarerank3("AtildeDD_dD", "sym01")
AtildeDD_dKOD = ixp.declarerank3("AtildeDD_dKOD", "sym01")
Theta_dD = ixp.declarerank1("Theta_dD")
Theta_dKOD = ixp.declarerank1("Theta_dKOD")
GammatildeU_dD = ixp.declarerank2("GammatildeU_dD", None)
GammatildeU_dKOD = ixp.declarerank2("GammatildeU_dKOD", None)
alphaG_dD = ixp.declarerank1("alphaG_dD")
alphaG_dDD = ixp.declarerank2("alphaG_dDD", "sym01")
alphaG_dKOD = ixp.declarerank1("alphaG_dKOD")
betaGU_dD = ixp.declarerank2("betaGU_dD", None)
betaGU_dDD = ixp.declarerank3("betaGU_dDD", "sym12")
betaGU_dKOD = ixp.declarerank2("betaGU_dKOD", None)

# Our tile-local derivatives
gfparams(gf_type="TILE_TMP",symmetries="sym01",centering=centering)
gfdecl("dchi",[la],"ddchi",[la,lb],"dbetaGchi","disschi",[],"dgammatilde",[la,lb,lc])

gfparams(gf_type="TILE_TMP",symmetries="sym01_sym23",centering=centering)
gfdecl("ddgammatilde",[la,lb,lc,ld])

gfparams(gf_type="TILE_TMP",symmetries="sym01",centering=centering)
gfdecl("dissgammatilde",[la,lb],"dKhat",[la],"dissKhat",[],"dAtilde",[la,lb,lc],"dissAtilde",[la,lb],\
    "dTheta",[la],"dissTheta",[])

gfparams(gf_type="TILE_TMP",symmetries="",centering=centering)
gfdecl("dGammatilde",[ua,lb],"dissGammatilde",[ua],"dalphaG",[la])

gfparams(gf_type="TILE_TMP",symmetries="sym01",centering=centering)
gfdecl("ddalphaG",[la,lb],"dissalphaG",[])

gfparams(gf_type="TILE_TMP",symmetries="",centering=centering)
gfdecl("dbetaG",[ua,lb])

gfparams(gf_type="TILE_TMP",symmetries="sym12",centering=centering)
gfdecl("ddbetaG",[ua,lb,lc],"dissbetaG",[ua])

# Expressions

gUU_expr, detg_expr = ixp.symm_matrix_inverter3x3(gDD)
gammatildeUU_expr, detgammatilde_expr = ixp.symm_matrix_inverter3x3(gammatildeDD)

# Initial conditions

gfparams(gf_type="SCALAR_TMP",symmetries="sym01",centering=centering)
gfdecl("g","gammatilde",[ua,ub],"dgammatilde",[ua,ub,lc],"Theta_val","trK","chi_val",[])

def Initial():
    initial1_eqns = [
        [lhrh(lhs=chi_val, rhs=1 / cbrt(detg_expr))],
        #[lhrh(lhs=gUU[i][j], rhs=gUU_expr[i][j]) for i in range(3) for j in range(i+1)],
        geneqns(lhs=g[ua,ub],values=gUU_expr),
        [lhrh(lhs=Theta_val, rhs=sympify(0))],
        #[lhrh(lhs=trK, rhs=sum2_symm(lambda x, y: gUU[x][y] * kDD[x][y]))],
        geneqns(lhs=trK, rhs=g[ua,ub]*k[la,lb]),
        [lhrh(lhs=chi, rhs=chi_val)],
        #[lhrh(lhs=gammatildeDD[i][j], rhs=chi_val * gDD[i][j]) for i in range(3) for j in range(i+1)],
        #geneqns2(lhs=gammatilde[li,lj], rhs=r"\text{chi_val} g_{i j}"),
        geneqns3(r"\tilde{\gamma}_{i j} = \text{chi_val} g_{i j}"),
        [lhrh(lhs=Theta, rhs=Theta_val)],
        [lhrh(lhs=Khat, rhs=trK - 2 * Theta_val)],
        #[lhrh(lhs=AtildeDD[i][j], rhs=chi_val * (kDD[i][j] - trK / 3 * gDD[i][j])) for i in range(3) for j in range(i+1)],
        geneqns3(r'\tilde{A}_{i j} = \text{chi_val} ( k_{i j} - \text{trK}/3 g_{i j})'),
        #geneqns2(lhs=Atilde[li,lj], rhs=r"\text{chi_val} (k_{i j} - \text{trK} g_{i j} / 3)"),
        [lhrh(lhs=alphaG, rhs=alp)],
        #[lhrh(lhs=betaGU[i], rhs=betaU[i]) for i in range(3)],
        geneqns2(lhs=betaG[ui], rhs=r"\beta^i"),
    ]

    thorn.add_func(
        "Z4cNRPy_Initial1",
        body=initial1_eqns,
        where='everywhere',
        schedule_bin="Z4cNRPy_InitialGroup",
        doc="Convert ADM to Z4c variables, part 1",
        centering=centering)
    
    initial2_eqns = [
        #[[
        #    [lhrh(lhs=dgammatildeDDD[i][j][k], rhs=gammatildeDD_dD[i][j][k]) for k in range(3)],
        #    [loop],
        #] for i in range(3) for j in range(i+1)],
        # Note, not adding loop after every equation. Is this desired?
        geneqns(lhs=dgammatilde[li,lj,lk], values=gammatildeDD_dD),
        loop,
        #[lhrh(lhs=gammatildeUU[i][j],
        #      rhs=gammatildeUU_expr[i][j])
        # for i in range(3) for j in range(i+1)],
        geneqns(lhs=gammatilde[ua,ub],values=gammatildeUU_expr),
        #[lhrh(lhs=dgammatildeUUD[i][j][k],
        #      rhs=- sum2_symm(lambda x, y: gammatildeUU[i][x] * gammatildeUU[j][y] * dgammatildeDDD[x][y][k]))
        # for i in range(3) for j in range(i+1) for k in range(3)],
        geneqns(lhs=dgammatilde[ui,uj,lk], rhs=gammatilde[ui,ux] * gammatilde[uj,uy] * dgammatilde[lx,ly,lk]),
        #[[lhrh(lhs=GammatildeU[i],
        #       rhs=- sum1(lambda x: dgammatildeUUD[i][x][x]))]
        # for i in range(3)],
        geneqns(lhs=Gammatilde[ui], rhs=dgammatilde[ui,ux,lx])
    ]
    
    thorn.add_func(
        "Z4cNRPy_Initial2",
        body=initial2_eqns,
        where='interior',
        schedule_bin="Z4cNRPy_InitialGroup AFTER Z4cNRPy_Initial1",
        doc="Convert ADM to Z4c variables, part 2",
        sync="GammatildeUGF",
        centering=centering)
Initial()

# Enforce constraints

gfparams(gf_type="SCALAR_TMP",centering=centering)
gfdecl("detgammatilde","trAtilde",[])
#detgammatilde = thorn.register_gridfunctions("SCALAR_TMP", ["detgammatilde"], centering=centering)
#trAtilde = thorn.register_gridfunctions("SCALAR_TMP", ["trAtilde"], centering=centering)

def Enforce():
    enforce_eqns = [
        # Enforce floors
        #[lhrh(lhs=gammatildeUU[i][j], rhs=gammatildeUU_expr[i][j]) for i in range(3) for j in range(i+1)],
        geneqns(lhs=gammatilde[ua,ub],values=gammatildeUU_expr),
        [lhrh(lhs=detgammatilde, rhs=detgammatilde_expr)],
        #[lhrh(lhs=trAtilde, rhs=sum2_symm(lambda x, y: gammatildeUU[x][y] * AtildeDD[x][y]))],
        geneqns(lhs=trAtilde, rhs=gammatilde[ux,uy]*Atilde[lx,ly]),
        [lhrh(lhs=chi, rhs=Max(chi_floor, chi))],
        [lhrh(lhs=alphaG, rhs=Max(alphaG_floor, alphaG))],
        # Enforce algebraic constraints; see arXiv:1212.2901 [gr-qc]
        #[lhrh(lhs=gammatildeDD[i][j], rhs=(1 / cbrt(detgammatilde)) * gammatildeDD[i][j]) for i in range(3) for j in range(i+1)],
        geneqns(lhs=gammatilde[li,lj], rhs=(1 / cbrt(detgammatilde)) * gammatilde[li,lj]),
        #[lhrh(lhs=AtildeDD[i][j], rhs=(AtildeDD[i][j] - trAtilde / 3 * gammatildeDD[i][j])) for i in range(3) for j in range(i+1)],
        geneqns(lhs=Atilde[li,lj], rhs=(Atilde[li,lj] - trAtilde / 3 * gammatilde[li,lj]))
    ]
    
    thorn.add_func(
        "Z4cNRPy_Enforce",
        body=enforce_eqns,
        # where='interior',
        where='everywhere',
        schedule_bin="Z4cNRPy_PostStepGroup",
        doc="Enforce constraints",
        # sync="chiGF gammatildeDDGF KhatGF AtildeDDGF GammatildeUGF ThetaGF alphaGGF betaGUGF",
        centering=centering
        )
Enforce()

# Calculate ADM variables
def ADM():
    adm_eqns = [
        #[lhrh(lhs=gDD[i][j], rhs=1 / chi * gammatildeDD[i][j]) for i in range(3) for j in range(i+1)],
        geneqns3(r"g_{i j} = 1/\chi \tilde{\gamma}_{i j}"),
        #[lhrh(lhs=kDD[i][j], rhs=1 / chi * (AtildeDD[i][j] + (Khat + 2 * Theta) / 3 * gammatildeDD[i][j]))
        # for i in range(3) for j in range(i+1)],
        geneqns3(r"k_{i j} = 1/\chi (\tilde{A}_{i j} + (\hat{K} + 2 \Theta) / 3 \tilde{\gamma}_{i j})"),
        [lhrh(lhs=alp, rhs=alphaG)],
        [lhrh(lhs=dtalp, rhs=-alphaG * f_mu_L * Khat)],
        #[lhrh(lhs=betaU[i], rhs=betaGU[i]) for i in range(3)],
        geneqns3(r"\beta^i = \text{betaG}^i"),
        #[lhrh(lhs=dtbetaU[i], rhs=f_mu_S * GammatildeU[i] - eta * betaGU[i]) for i in range(3)],
        geneqns(lhs=dtbeta[ui], rhs=f_mu_S * Gammatilde[ui] - eta * betaG[ui])
    ]
    
    thorn.add_func(
        "Z4cNRPy_ADM",
        body=adm_eqns,
        # where='interior',
        where='everywhere',
        schedule_bin="Z4cNRPy_PostStepGroup AFTER Z4cNRPy_Enforce",
        doc="Calculate ADM variables",
        # sync="ADMBase::metric ADMBase::curv ADMBase::lapse ADMBase::dtlapse ADMBase::shift ADMBase::dtshift",
        centering=centering)
ADM()

# Calculate RHS

gfparams(gf_type="SCALAR_TMP",symmetries="sym01",centering=centering)
gfdecl("dg",[la,lb,lc])

gfparams(gf_type="SCALAR_TMP",symmetries="sym12",centering=centering)
gfdecl("Gamma",[la,lb,lc],"Gamma",[ua,lb,lc])

gfparams(gf_type="SCALAR_TMP",symmetries="sym01",centering=centering)
gfdecl("DDalphaG",[la,lb])

DbetaGUD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "DbetaGUD", None, centering=centering)
rho = thorn.register_gridfunctions("SCALAR_TMP", ["rho"], centering=centering)
SiD = ixp.register_gridfunctions_for_single_rankN(1, "SCALAR_TMP", "SiD", None, centering=centering)
SijDD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "SijDD", "sym01", centering=centering)
trS = thorn.register_gridfunctions("SCALAR_TMP", ["trS"], centering=centering)
AtildeUD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "AtildeUD", None, centering=centering)
AtildeUU = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "AtildeUU", "sym01", centering=centering)
dAtildeUDD = ixp.register_gridfunctions_for_single_rankN(3, "SCALAR_TMP", "dAtildeUDD", None, centering=centering)
dAtildeUUD = ixp.register_gridfunctions_for_single_rankN(3, "SCALAR_TMP", "dAtildeUUD", "sym01", centering=centering)
GammatildeDDD = ixp.register_gridfunctions_for_single_rankN(3, "SCALAR_TMP", "GammatildeDDD", "sym12", centering=centering)
GammatildeUDD = ixp.register_gridfunctions_for_single_rankN(3, "SCALAR_TMP", "GammatildeUDD", "sym12", centering=centering)
GammatildeUDU = ixp.register_gridfunctions_for_single_rankN(3, "SCALAR_TMP", "GammatildeUDU", None, centering=centering)
GammatildedirectU = ixp.register_gridfunctions_for_single_rankN(1, "SCALAR_TMP", "GammatildedirectU", None, centering=centering)
DDchiDD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "DDchiDD", "sym01", centering=centering)
RchiDD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "RchiDD", "sym01", centering=centering)
RtildeDD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "RtildeDD", "sym01", centering=centering)
RDD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "RDD", "sym01", centering=centering)
Rsc = thorn.register_gridfunctions("SCALAR_TMP", ["Rsc"], centering=centering)
alphaRicciTmunuDD = ixp.register_gridfunctions_for_single_rankN(2, "SCALAR_TMP", "alphaRicciTmunuDD", "sym01", centering=centering)
ZetatildeCvalU = ixp.register_gridfunctions_for_single_rankN(1, "SCALAR_TMP", "ZetatildeCvalU", None, centering=centering)
HCval = thorn.register_gridfunctions("SCALAR_TMP", ["HCval"], centering=centering)
MtildeCvalU = ixp.register_gridfunctions_for_single_rankN(1, "SCALAR_TMP", "MtildeCvalU", None, centering=centering)

def RHS():
    rhs_eqns = [
        # Derivatives
        [
            #[lhrh(lhs=dchiD[i], rhs=chi_dD[i]) for i in range(3)],
            geneqns(lhs=dchi[li], rhs=chi_d[li]),
            [lhrh(lhs=ddchiDD[i][j], rhs=chi_dDD[i][j]) for i in range(3) for j in range(i+1)],
            #geneqns(lhs=ddchi[li,lj], rhs=chi_d[li,lj]),
            # [lhrh(lhs=dbetaGchi, rhs=sum1(lambda x: (+ betaGU[x] * (chi_dupD[x] + chi_ddnD[x])
            #                                          + abs(betaGU[x]) * (chi_dupD[x] - chi_ddnD[x])) / 2))],
            # [lhrh(lhs=disschi, rhs=sum1(lambda x: chi_dKOD[x]))],
            [loop],
        ],
        [[
            [lhrh(lhs=dgammatildeDDD[i][j][k], rhs=gammatildeDD_dD[i][j][k]) for k in range(3)],
            [lhrh(lhs=ddgammatildeDDDD[i][j][k][l], rhs=gammatildeDD_dDD[i][j][k][l]) for k in range(3) for l in range(k+1)],
            # [lhrh(lhs=dissgammatildeDD[i][j], rhs=sum1(lambda x: gammatildeDD_dKOD[i][j][x]))],
            [loop],
        ] for i in range(3) for j in range(i+1)],
        [[
            [lhrh(lhs=dGammatildeUD[i][j], rhs=GammatildeU_dD[i][j]) for j in range(3)],
            # [lhrh(lhs=dissGammatildeU[i], rhs=sum1(lambda x: GammatildeU_dKOD[i][x]))],
            [loop],
        ] for i in range(3)],
        [
            [lhrh(lhs=dKhatD[i], rhs=Khat_dD[i]) for i in range(3)],
            # [lhrh(lhs=dissKhat, rhs=sum1(lambda x: Khat_dKOD[x]))],
            [loop],
        ],
        [[
            [lhrh(lhs=dAtildeDDD[i][j][k], rhs=AtildeDD_dD[i][j][k]) for k in range(3)],
            # [lhrh(lhs=dissAtildeDD[i][j], rhs=sum1(lambda x: AtildeDD_dKOD[i][j][x]))],
            [loop],
        ] for i in range(3) for j in range(i+1)],
        [
            [lhrh(lhs=dThetaD[i], rhs=Theta_dD[i]) for i in range(3)],
            # [lhrh(lhs=dissTheta, rhs=sum1(lambda x: Theta_dKOD[x]))],
            [loop],
        ],
        [
            [lhrh(lhs=dalphaGD[i], rhs=alphaG_dD[i]) for i in range(3)],
            [lhrh(lhs=ddalphaGDD[i][j], rhs=alphaG_dDD[i][j]) for i in range(3) for j in range(i+1)],
            # [lhrh(lhs=dissalphaG, rhs=sum1(lambda x: alphaG_dKOD[x]))],
            [loop],
        ],
        [[
            [lhrh(lhs=dbetaGUD[i][j], rhs=betaGU_dD[i][j]) for j in range(3)],
            [lhrh(lhs=ddbetaGUDD[i][j][k], rhs=betaGU_dDD[i][j][k]) for j in range(3) for k in range(j+1)],
            # [lhrh(lhs=dissbetaGU[i], rhs=sum1(lambda x: betaGU_dKOD[i][x]))],
            [loop],
        ] for i in range(3)],

        # RHS
        [lhrh(lhs=gammatildeUU[i][j],
              rhs=gammatildeUU_expr[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=gUU[i][j],
              rhs=chi * gammatildeUU[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=dgDDD[i][j][k],
              rhs=(- 1 / chi**2 * dchiD[k] * gammatildeDD[i][j]
                   + 1 / chi * dgammatildeDDD[i][j][k]))
         for i in range(3) for j in range(i+1) for k in range(3)],
        [lhrh(lhs=GammaDDD[i][j][k],
              rhs=Rational(1,2) * (dgDDD[i][j][k] + dgDDD[i][k][j] - dgDDD[j][k][i]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=GammaUDD[i][j][k],
              rhs=sum1(lambda x: gUU[i][x] * GammaDDD[x][j][k]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=DbetaGUD[i][j],
              rhs=dbetaGUD[i][j] + sum1(lambda x: GammaUDD[i][x][j] * betaGU[x]))
         for i in range(3) for j in range(3)],
        # arXiv:1212.2901 [gr-qc], (1)
        [lhrh(lhs=rhs_chi,
              rhs=(+ Rational(2,3) * chi * (alphaG * (Khat + 2 * Theta) - sum1(lambda x: DbetaGUD[x][x]))
                   # - Rational(2,3) * sum1(lambda x: betaGU[x] * dchiD[x])
                   # + Rational(2,3) * dbetaGchi
                   # + eps_diss * disschi
                   ))],

        # arXiv:1212.2901 [gr-qc], (2)
        [lhrh(lhs=rhs_gammatildeDD[i][j],
              rhs=(-2 * alphaG * AtildeDD[i][j]
                   + sum1(lambda x: betaGU[x] * dgammatildeDDD[i][j][x])
                   + sum1(lambda x: gammatildeDD[x][i] * dbetaGUD[x][j] + gammatildeDD[x][j] * dbetaGUD[x][i])
                   - Rational(2,3) * sum1(lambda x: gammatildeDD[i][j] * dbetaGUD[x][x])
                   # + eps_diss * dissgammatildeDD[i][j]
                   ))
         for i in range(3) for j in range(i+1)],

        [lhrh(lhs=DDalphaGDD[i][j],
              rhs=ddalphaGDD[i][j] - sum1(lambda x: GammaUDD[x][i][j] * dalphaGD[x]))
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=AtildeUD[i][j],
              rhs=sum1(lambda x: gammatildeUU[i][x] * AtildeDD[x][j]))
         for i in range(3) for j in range(3)],
        [lhrh(lhs=rho,
              rhs=1 / alphaG**2 * (+ eTtt
                                   - 2 * sum1(lambda x: betaGU[x] * eTtD[x])
                                   + sum2_symm(lambda x, y: betaGU[x] * betaGU[y] * eTDD[x][y])))],
        [lhrh(lhs=SiD[i],
              rhs=-1 / alphaG * (eTtD[i] - sum1(lambda x:  betaGU[x] * eTDD[i][x])))
         for i in range(3)],
        [lhrh(lhs=SijDD[i][j],
              rhs=eTDD[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=trS,
              rhs=sum2_symm(lambda x, y: gUU[x][y] * SijDD[x][y]))],
        # arXiv:1212.2901 [gr-qc], (3)
        [lhrh(lhs=rhs_Khat,
              rhs=(- sum2_symm(lambda x, y: gUU[x][y] * DDalphaGDD[x][y])
                   + alphaG * (+ sum2_symm(lambda x, y: AtildeUD[x][y] * AtildeUD[y][x])
                               + Rational(1,3) * (Khat + 2 * Theta)**2)
                   + 4 * pi * alphaG * (trS + rho)
                   + alphaG * kappa1 * (1 - kappa2) * Theta
                   + sum1(lambda x: betaGU[x] * dKhatD[x])
                   # + eps_diss * dissKhat
                   ))],

        [lhrh(lhs=GammatildeDDD[i][j][k],
              rhs=Rational(1,2) * (dgammatildeDDD[i][j][k] + dgammatildeDDD[i][k][j] - dgammatildeDDD[j][k][i]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=GammatildeUDD[i][j][k],
              rhs=sum1(lambda x: gammatildeUU[i][x] * GammatildeDDD[x][j][k]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=GammatildeUDU[i][j][k],
              rhs=sum1(lambda x: GammatildeUDD[i][j][x] * gammatildeUU[x][k]))
         for i in range(3) for j in range(3) for k in range(3)],
        [lhrh(lhs=GammatildedirectU[i],
              rhs=sum1(lambda x: GammatildeUDU[i][x][x]))
         for i in range(3)],
        [lhrh(lhs=DDchiDD[i][j],
              rhs=ddchiDD[i][j] - sum1(lambda x: GammatildeUDD[x][i][j] * dchiD[x]))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (8)
        [lhrh(lhs=RchiDD[i][j],
              rhs=(+ Rational(1,2) / chi * DDchiDD[i][j]
                   + Rational(1,2) / chi * gammatildeDD[i][j] * sum2_symm(lambda x, y: gammatildeUU[x][y] * DDchiDD[x][y])
                   - Rational(1,4) / chi**2 * dchiD[i] * dchiD[j]
                   - Rational(3,4) / chi**2 * (gammatildeDD[i][j] *
                                               sum2_symm(lambda x, y: gammatildeUU[x][y] * dchiD[x] * dchiD[y]))))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (9)
        [lhrh(lhs=RtildeDD[i][j],
              rhs=(- Rational(1,2) * sum2_symm(lambda x, y: gammatildeUU[x][y] * ddgammatildeDDDD[i][j][x][y])
                   + Rational(1,2) * sum1(lambda x: (+ gammatildeDD[x][i] * dGammatildeUD[x][j]
                                                     + gammatildeDD[x][j] * dGammatildeUD[x][i]))
                   + Rational(1,2) * sum1(lambda x: (+ GammatildedirectU[x] * GammatildeDDD[i][j][x]
                                                     + GammatildedirectU[x] * GammatildeDDD[j][i][x]))
                   + sum2_symm(lambda x, y: (+ GammatildeUDD[x][i][y] * GammatildeUDU[j][x][y]
                                             + GammatildeUDD[x][j][y] * GammatildeUDU[i][x][y]
                                             + GammatildeUDD[x][i][y] * GammatildeUDU[x][j][y]))))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (7)
        [lhrh(lhs=RDD[i][j],
              rhs=RchiDD[i][j] + RtildeDD[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=Rsc,
              rhs=sum2_symm(lambda x, y: gUU[x][y] * RDD[x][y]))],
        [lhrh(lhs=alphaRicciTmunuDD[i][j],
              rhs=- DDalphaGDD[i][j] + alphaG * (RDD[i][j] - 8 * pi * SijDD[i][j]))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (4)
        [lhrh(lhs=rhs_AtildeDD[i][j],
              rhs=(+ chi * (alphaRicciTmunuDD[i][j]
                            - (Rational(1,3) * gammatildeDD[i][j] *
                               sum2_symm(lambda x, y: gammatildeUU[x][y] * alphaRicciTmunuDD[x][y])))
                   + alphaG * (+ (Khat + 2 * Theta) * AtildeDD[i][j]
                               - 2 * sum1(lambda x: AtildeDD[x][i] * AtildeUD[x][j]))
                   + sum1(lambda x: betaGU[x] * dAtildeDDD[i][j][x])
                   + sum1(lambda x: AtildeDD[x][i] * dbetaGUD[x][j] + AtildeDD[x][j] * dbetaGUD[x][i])
                   - Rational(2,3) * AtildeDD[i][j] * sum1(lambda x: dbetaGUD[x][x])
                   # + eps_diss * dissAtildeDD[i][j]
                   ))
         for i in range(3) for j in range(i+1)],

        [lhrh(lhs=AtildeUU[i][j],
              rhs=sum1(lambda x: gammatildeUU[i][x] * AtildeUD[j][x]))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (5)
        [lhrh(lhs=rhs_GammatildeU[i],
              rhs=(- 2 * sum1(lambda x: AtildeUU[i][x] * dalphaGD[x])
                   + 2 * alphaG *
                         (+ sum2_symm(lambda x, y: GammatildeUDD[i][x][y] * AtildeUU[x][y])
                          - Rational(3,2) / chi * sum1(lambda x: AtildeUU[i][x] * dchiD[x])
                          - Rational(1,3) * sum1(lambda x: gammatildeUU[i][x] * (2 * dKhatD[x] + dThetaD[x]))
                          - 8 * pi * sum1(lambda x: gammatildeUU[i][x] * SiD[x]))
                   + sum2_symm(lambda x, y: gammatildeUU[x][y] * ddbetaGUDD[i][x][y])
                   + Rational(1,3) * sum2(lambda x, y: gammatildeUU[i][x] * ddbetaGUDD[y][x][y])
                   + sum1(lambda x: betaGU[x] * dGammatildeUD[i][x])
                   - sum1(lambda x: GammatildedirectU[x] * dbetaGUD[i][x])
                   + Rational(2,3) * GammatildedirectU[i] * sum1(lambda x: dbetaGUD[x][x])
                   - 2 * alphaG * kappa1 * (GammatildeU[i] - GammatildedirectU[i])
                   # + eps_diss * dissGammatildeU[i]
                   ))
         for i in range(3)],

        # arXiv:1212.2901 [gr-qc], (6)
        [lhrh(lhs=rhs_Theta,
              rhs=Piecewise((0, set_Theta_zero),
                            ((+ Rational(1,2) * alphaG * (+ Rsc
                                                          - sum2_symm(lambda x, y: AtildeUU[x][y] * AtildeDD[x][y])
                                                          + Rational(2,3) * (Khat + 2 * Theta)**2)
                              - alphaG * (+ 8 * pi * rho
                                          + kappa1 * (2 + kappa2) * Theta)
                              + sum1(lambda x: betaGU[x] * dThetaD[x])
                              # + eps_diss * dissTheta
                              ), True)))],

        [lhrh(lhs=rhs_alphaG,
              rhs=(- alphaG * f_mu_L * Khat
                   # + eps_diss * dissalphaG
                   ))],

        [lhrh(lhs=rhs_betaGU[i],
              rhs=(+ f_mu_S * GammatildeU[i] - eta * betaGU[i]
                   # + eps_diss * dissbetaGU[i]
                   ))
         for i in range(3)],
        [loop],

        [
            [lhrh(lhs=rhs_chi, rhs=rhs_chi + eps_diss * sum1(lambda x: chi_dKOD[x]))],
            [loop],
        ],
        [[
            [lhrh(lhs=rhs_gammatildeDD[i][j], rhs=rhs_gammatildeDD[i][j] + eps_diss * sum1(lambda x: gammatildeDD_dKOD[i][j][x]))],
            [loop],
        ] for i in range(3) for j in range(i+1)],
        [[
            [lhrh(lhs=rhs_GammatildeU[i], rhs=rhs_GammatildeU[i] + eps_diss * sum1(lambda x: GammatildeU_dKOD[i][x]))],
            [loop],
        ] for i in range(3)],
        [
            [lhrh(lhs=rhs_Khat, rhs=rhs_Khat + eps_diss * sum1(lambda x: Khat_dKOD[x]))],
            [loop],
        ],
        [[
            [lhrh(lhs=rhs_AtildeDD[i][j], rhs=rhs_AtildeDD[i][j] + eps_diss * sum1(lambda x: AtildeDD_dKOD[i][j][x]))],
            [loop],
        ] for i in range(3) for j in range(i+1)],
        [
            [lhrh(lhs=rhs_Theta, rhs=rhs_Theta + eps_diss * sum1(lambda x: Theta_dKOD[x]))],
            [loop],
        ],
        [
            [lhrh(lhs=rhs_alphaG, rhs=rhs_alphaG + eps_diss * sum1(lambda x: alphaG_dKOD[x]))],
            [loop],
        ],
        [[
            [lhrh(lhs=rhs_betaGU[i], rhs=rhs_betaGU[i] + eps_diss * sum1(lambda x: betaGU_dKOD[i][x]))],
            [loop],
        ] for i in range(3)],
    ]
    
    thorn.add_func(
        "Z4cNRPy_RHS",
        body=rhs_eqns,
        where='interior',
        schedule_bin="ODESolvers_RHS",
        doc="Calculate RHS",
        sync="rhs_chiGF rhs_gammatildeDDGF rhs_KhatGF rhs_AtildeDDGF rhs_GammatildeUGF rhs_ThetaGF rhs_alphaGGF rhs_betaGUGF",
        centering=centering)
RHS()

# Evaluate constraints

def Constraints():
    constraints_eqns = [
        # Derivatives
        [
            [lhrh(lhs=dchiD[i], rhs=chi_dD[i]) for i in range(3)],
            [lhrh(lhs=ddchiDD[i][j], rhs=chi_dDD[i][j]) for i in range(3) for j in range(i+1)],
            [loop],
        ],
        [[
            [lhrh(lhs=dgammatildeDDD[i][j][k], rhs=gammatildeDD_dD[i][j][k]) for k in range(3)],
            [lhrh(lhs=ddgammatildeDDDD[i][j][k][l], rhs=gammatildeDD_dDD[i][j][k][l]) for k in range(3) for l in range(k+1)],
            [loop],
        ] for i in range(3) for j in range(i+1)],
        [[
            [lhrh(lhs=dGammatildeUD[i][j], rhs=GammatildeU_dD[i][j]) for j in range(3)],
            [loop],
        ] for i in range(3)],
        [[
            [lhrh(lhs=dAtildeDDD[i][j][k], rhs=AtildeDD_dD[i][j][k]) for k in range(3)],
            [loop],
        ] for i in range(3) for j in range(i+1)],
        [
            [lhrh(lhs=dKhatD[i], rhs=Khat_dD[i]) for i in range(3)],
            [loop],
        ],
        [
            [lhrh(lhs=dThetaD[i], rhs=Theta_dD[i]) for i in range(3)],
            [loop],
        ],

        # Constraints

        # ZetatildeC, eqn. (13)
        [lhrh(lhs=gammatildeUU[i][j],
              rhs=gammatildeUU_expr[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=GammatildeDDD[i][j][k],
              rhs=Rational(1,2) * (dgammatildeDDD[i][j][k] + dgammatildeDDD[i][k][j] - dgammatildeDDD[j][k][i]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=GammatildeUDD[i][j][k],
              rhs=sum1(lambda x: gammatildeUU[i][x] * GammatildeDDD[x][j][k]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=GammatildeUDU[i][j][k],
              rhs=sum1(lambda x: GammatildeUDD[i][j][x] * gammatildeUU[x][k]))
         for i in range(3) for j in range(3) for k in range(3)],
        [lhrh(lhs=GammatildedirectU[i],
              rhs=sum1(lambda x: GammatildeUDU[i][x][x]))
         for i in range(3)],
        [lhrh(lhs=ZetatildeCvalU[i],
              rhs=(GammatildeU[i] - GammatildedirectU[i]) / 2)
         for i in range(3)],
        [lhrh(lhs=ZetatildeCU[i],
              rhs=(ZetatildeCvalU[i]))
         for i in range(3)],

        # HC, eqn. (14)
        [lhrh(lhs=gUU[i][j],
              rhs=chi * gammatildeUU[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=dgDDD[i][j][k],
              rhs=(- 1 / chi**2 * dchiD[k] * gammatildeDD[i][j]
                   + 1 / chi * dgammatildeDDD[i][j][k]))
         for i in range(3) for j in range(i+1) for k in range(3)],
        [lhrh(lhs=GammaDDD[i][j][k],
              rhs=Rational(1,2) * (dgDDD[i][j][k] + dgDDD[i][k][j] - dgDDD[j][k][i]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=GammaUDD[i][j][k],
              rhs=sum1(lambda x: gUU[i][x] * GammaDDD[x][j][k]))
         for i in range(3) for j in range(3) for k in range(j+1)],
        [lhrh(lhs=AtildeUD[i][j],
              rhs=sum1(lambda x: gammatildeUU[i][x] * AtildeDD[x][j]))
         for i in range(3) for j in range(3)],
        [lhrh(lhs=rho,
              rhs=1 / alphaG**2 * (+ eTtt
                                   - 2 * sum1(lambda x: betaGU[x] * eTtD[x])
                                   + sum2_symm(lambda x, y: betaGU[x] * betaGU[y] * eTDD[x][y])))],
        [lhrh(lhs=DDchiDD[i][j],
              rhs=ddchiDD[i][j] - sum1(lambda x: GammatildeUDD[x][i][j] * dchiD[x]))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (8)
        [lhrh(lhs=RchiDD[i][j],
              rhs=(+ Rational(1,2) / chi * DDchiDD[i][j]
                   + Rational(1,2) / chi * gammatildeDD[i][j] * sum2_symm(lambda x, y: gammatildeUU[x][y] * DDchiDD[x][y])
                   - Rational(1,4) / chi**2 * dchiD[i] * dchiD[j]
                   - Rational(3,4) / chi**2 * (gammatildeDD[i][j] *
                                               sum2_symm(lambda x, y:  gammatildeUU[x][y] * dchiD[x] * dchiD[y]))))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (9)
        [lhrh(lhs=RtildeDD[i][j],
              rhs=(- Rational(1,2) * sum2_symm(lambda x, y: gammatildeUU[x][y] * ddgammatildeDDDD[i][j][x][y])
                   + Rational(1,2) * sum1(lambda x: (+ gammatildeDD[x][i] * dGammatildeUD[x][j]
                                                     + gammatildeDD[x][j] * dGammatildeUD[x][i]))
                   + Rational(1,2) * sum1(lambda x: (+ GammatildedirectU[x] * GammatildeDDD[i][j][x]
                                                     + GammatildedirectU[x] * GammatildeDDD[j][i][x]))
                   + sum2_symm(lambda x, y: (+ GammatildeUDD[x][i][y] * GammatildeUDU[j][x][y]
                                             + GammatildeUDD[x][j][y] * GammatildeUDU[i][x][y]
                                             + GammatildeUDD[x][i][y] * GammatildeUDU[x][j][y]))))
         for i in range(3) for j in range(i+1)],
        # arXiv:1212.2901 [gr-qc], (7)
        [lhrh(lhs=RDD[i][j],
              rhs=RchiDD[i][j] + RtildeDD[i][j])
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=Rsc,
              rhs=sum2_symm(lambda x, y: gUU[x][y] * RDD[x][y]))],
        # arXiv:1212.2901 [gr-qc], (14)
        [lhrh(lhs=HCval,
              rhs=(+ Rsc
                   + sum2_symm(lambda x, y: AtildeUD[x][y] * AtildeUD[y][x])
                   - Rational(2,3) * (Khat + 2 * Theta)**2
                   - 16 * pi * rho))],
        [lhrh(lhs=HC,
              rhs=HCval)],

        # MtildeC, eqn. (15)
        [lhrh(lhs=AtildeUU[i][j],
              rhs=sum1(lambda x: gammatildeUU[i][x] * AtildeUD[j][x]))
         for i in range(3) for j in range(i+1)],
        [lhrh(lhs=dgammatildeUUD[i][j][k],
              rhs=- sum2_symm(lambda x, y: gammatildeUU[i][x] * gammatildeUU[j][y] * dgammatildeDDD[x][y][k]))
         for i in range(3) for j in range(i+1) for k in range(3)],
        [lhrh(lhs=dAtildeUDD[i][j][k],
              rhs=(+ sum1(lambda x: dgammatildeUUD[i][x][k] * AtildeDD[x][j])
                   + sum1(lambda x: gammatildeUU[i][x] * dAtildeDDD[x][j][k])))
         for i in range(3) for j in range(3) for k in range(3)],
        [lhrh(lhs=dAtildeUUD[i][j][k],
              rhs=(+ sum1(lambda x: dgammatildeUUD[i][x][k] * AtildeUD[j][x])
                   + sum1(lambda x: gammatildeUU[i][x] * dAtildeUDD[j][x][k])))
         for i in range(3) for j in range(i+1) for k in range(3)],
        [lhrh(lhs=SiD[i],
              rhs=-1 / alphaG * (eTtD[i] - sum1(lambda x:  betaGU[x] * eTDD[i][x])))
         for i in range(3)],
        # arXiv:1212.2901 [gr-qc], (15)
        [lhrh(lhs=MtildeCvalU[i],
              rhs=(+ sum1(lambda x: dAtildeUUD[i][x][x])
                   + sum2_symm(lambda x, y: GammatildeUDD[i][x][y] * AtildeUU[x][y])
                   - Rational(2,3) * sum1(lambda x: gammatildeUU[i][x] * (dKhatD[x] + 2 * dThetaD[x]))
                   - Rational(2,3) * sum1(lambda x: AtildeUU[i][x] * dchiD[x] / chi)
                   - 8 * pi * sum1(lambda x: gammatildeUU[i][x] * SiD[x])))
         for i in range(3)],
        [lhrh(lhs=MtildeCU[i],
              rhs=MtildeCvalU[i])
         for i in range(3)],

        # allC, arXiv:1111.2177, eqn. (73)
        [lhrh(lhs=allC,
              rhs=sqrt(Max(0, (+ HCval**2
                               + sum2_symm(lambda x, y: gammatildeDD[x][y] * MtildeCvalU[x] * MtildeCvalU[y])
                               + Theta**2
                               + 2 * sum2_symm(lambda x, y: gammatildeDD[x][y] * ZetatildeCvalU[x] * ZetatildeCvalU[y])))))],
    ]
    
    thorn.add_func(
        "Z4cNRPy_Constraints",
        body=constraints_eqns,
        where='interior',
        schedule_bin="Z4c_AnalysisGroup",
        doc="Evaluate Constraints",
        sync="ZetatildeCUGF HCGF MtildeCUGF allCGF",
        centering=centering)
Constraints()

# Generate thorn

assert "CACTUS_HOME" in os.environ, "Please set the CACTUS_HOME variable to point to your Cactus installation"
cactus_home = os.environ["CACTUS_HOME"]
cactus_sim = os.environ.get("CACTUS_SIM", "sim")
cactus_thornlist = os.environ.get("CACTUS_THORNLIST", None)

schedule_raw = """
# Define schedule groups

SCHEDULE GROUP Z4cNRPy_InitialGroup AT initial AFTER ADMBase_PostInitial
{
} "Convert ADM to Z4c variables"

SCHEDULE GROUP Z4cNRPy_PostStepGroup AT initial AFTER Z4cNRPy_InitialGroup BEFORE ADMBase_SetADMVars
{
} "Post-process Z4c variables"

SCHEDULE GROUP Z4cNRPy_PostStepGroup AT postregrid BEFORE ADMBase_SetADMVars
{
} "Post-process Z4c variables"

SCHEDULE GROUP Z4cNRPy_PostStepGroup IN ODESolvers_PostStep BEFORE ADMBase_SetADMVars
{
} "Post-process Z4c variables"

SCHEDULE GROUP Z4c_AnalysisGroup AT analysis
{
} "Analyse Z4c variables"
"""

thorn.generate(cactus_home, cactus_config=cactus_sim, cactus_thornlist=cactus_thornlist,schedule_raw=schedule_raw)
