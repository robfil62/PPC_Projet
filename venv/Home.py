from multiprocessing import Process,Queue,Lock,Value,Event,Array
import time
import random
import multiprocessing


nmbHome=10 #Définit le nombre de maisons
nmbTour=5   #Définit le nombre de tour avant l'arrêt de la simulation
delai=2   #Définit le temps d'attente entre chaque top d'horloge
starting_price=0.145    #Prix initiale

#Pour le calcul du prix :
gamma=0.99  #Coefficient influence du prix précédent
alpha=0.25  #Coefficient influence de la température
beta=0.25   #Coefficient influence du vent
theta=0.05  #Coefficient influence des échanges au tour précédent

def Home(ID,lockQueue,lockCount,queue,count,market_OK,lockWrite,clock_ok,temp,wind,weather_ok,num_policy):
    Money_Bal = 0
    Id = ID
    while clock_ok.wait(1.5*delai): #Attend le top de la clock, et si elle attend plus de 1.5*delai, sort et meurt

        flag_Market = False
        neg_Flag = False

        weather_ok.wait()
        Prod = random.randrange(1.0, 10.0) *wind[1]  #Production aléatoire (événements aléatoire dans la maison) + influence du vent
        Cons = random.randrange(1.0, 10.0) *temp[1]  #Consommation aléatoire (événements aléatoire dans la maison) + influence de la température (inversement proportionnel)
        Energy_Bal = Prod - Cons  # Calcul de Energy_Balance pour chaque Home
        with lockWrite:
            print("Energy n°", Id, " : ", Energy_Bal)

        if Energy_Bal < 0:  # Si Home en déficit :
            with lockQueue:
                queue.put([Id, Energy_Bal])  # Met sa demande dans la queue
            with lockCount:
                count.value += 1  # Annonce qu'elle a terminé de remplir

        else:  # Sinon :
            with lockCount:
                count.value += 1  # Ne fais rien et annonce qu'elle a terminé de remplir

        while count.value < nmbHome:  # Attend que toutes les Homes aient rempli la queue avec les demandes
            True

        clock_ok.clear()    #Réinitialise le flag de l'événement clock
        weather_ok.clear()  #Reinitialise le flage de l'événement weather
###########Les réinitialisation se font ici, une fois que toutes les homes ont utilisé les flags (Si on les fait avant, certaines homes vont restées bloquer à l'attente du flag)

        if Energy_Bal > 0 and (num_policy==1 or num_policy==3):  # Si la Home est en surplus :
            with lockQueue:
                while (Energy_Bal != 0 and (not queue.empty() or queue.qsize()!=0)):  # Tant qu'elle encore de l'énergie à donner et qu'il y a des demandes non traitées :
                    demande = queue.get()
                    if abs(demande[1]) <= Energy_Bal:  # Si la demande est réalisable:
                        Energy_Bal = Energy_Bal - abs(demande[1])  # Donne son énergie à la maison
                        with lockWrite:
                            print("Maison n° ", Id, "donne ", abs(demande[1]), "à maison", demande[0])
                    else:  # Si la demande est trop importante :
                        queue.put([demande[0],demande[1] + Energy_Bal])  # Donne son énergie restante et replace la demande mise à jour
                        with lockWrite:
                            print("Maison n° ",Id,"donne",Energy_Bal, "à maison",demande[0])
                        Energy_Bal = 0  # Son énergie devient nulle


        with lockCount:
            count.value += 1  # Annonce qu'elle a fini de donner son énergie

        while count.value < 2 * nmbHome:  # Attend toutes les Homes
            True

        if Energy_Bal < 0: # Si la Home est en déficit, regarde si quelqu'un à répondu à sa demande :
            Tab=[] #Crée un tableau où elle va mettre toutes les demandes qui ne la concerne pas
            with lockQueue:
                while not queue.empty() or queue.qsize()!=0 : # Tant que la queue n'est pas vide
                    demande = queue.get()#Récupère une demande
                    if demande[0] == Id:  # Regarde si la demande nous concerne
                        Energy_Bal = demande[1]  # Si oui, met à jour son Energy_Bal
                        neg_Flag = True
                        break
                    else:       #Si non, l'ajoute à son tableau
                        Tab.append(demande)

                for d in Tab:
                    queue.put(d)    #Une fois sortie, replace toutes les demandes de son tableau dans la queue

            if neg_Flag == False:  # Si la queue est vide et qu'elle n'a pas trouvé de demande la concernant
                Energy_Bal = 0  # Sa demande a été traitée entiérement, donc son Energy_Bal passe à 0


        if Energy_Bal != 0 and (num_policy==2 or num_policy==3):     #Une fois toutes les demandes traitées, si elles ont encore besoin d'énergies ou peuvent encore en donner
            with lockQueue:
                queue.put([Id, Energy_Bal]) #Place leur énergie dans la queue à destination du market
                flag_Market = True  #Si elles ont placées quelque chose pour le market, elles iront chercher la réponse de celui-ci
            Energy_Bal = 0  #Elle achète ou vend son énergie pour être à 0


        with lockCount:
            count.value += 1  # Annonce qu'elle est prête

        neg_Flag = False    #Réinitialisation

####### A ce stade, la queue ne contient que des demandes et des offres pour le marché ##########

        while market_OK.value == False: #Attend la réponse du market
            True

        if flag_Market :    #Si elle ont traité avec le marché
            Tab2=[] #Crée un tableau pour placer les demandes ne les concernant pas
            with lockQueue:
                while flag_Market == True:  #Tant qu'elles n'ont pas récupéré leur réponse
                    demande = queue.get()   #Récupère la première réponse dans la queue
                    if demande[0] == Id:    #Si elle nous concerne
                        Money_Bal += demande[1] #Modifie sa Money_Balance
                        flag_Market = False     #Elle a récupéré sa réponse, donc plus besoin de regarder le market
                    else:
                        Tab2.append(demande) #Sinon, l'ajoute à son tableau

                for d in Tab2:
                    queue.put(d)    #Une fois sortie, replace toutes les demandes ne la concernant pas

        count.value=0   #Réinitialisation du compteur ici, car il ne sera plus modifié dans ce tour d'horloge

        with lockWrite:
            print("Money n°", Id, " : ", Money_Bal)


def Market(queue,count,market_OK,clock_ok,temp,wind):
    currentPrice=starting_price
    moy_exchange=0.0
    Exchange=0.0
    while clock_ok.wait(1.5*delai):     #Attend le top de la clock au maximum pendant 1.5*delai
        market_OK.value=False

        #Annonce qu'il n'a pas mis à jour la queue avec les prix
        internal=alpha*temp[1]+beta*wind[1]-theta*moy_exchange #Calcul les effets internes(weather+echanges au tour précédent)
        external=0  #Calcul les effets externes
        currentPrice=gamma*currentPrice+internal+external #Calcul le nouveau prix

        if currentPrice<=0:
            currentPrice=starting_price
            print("NEGATIF")

        while count.value<3*nmbHome:    #Attend que toutes les homes aient mis leurs demandes pour le marché dans le queue
            True

        print("PRICE :",currentPrice)

        size=queue.qsize()  #Compte le nombre de demande qu'il a réaliser
        tab=[]  #Initialise son tableau pour stocker les demandes (permet le calcul de la moyenne des echanges)

        for i in range(0,size):
            demande=queue.get() #Récupère le demande
            tab.append(demande) #L'ajoute à son tableau

        for d in tab :
            queue.put([d[0],d[1]*currentPrice]) #Place l'argent correspondant aux demandes dans la queue

        market_OK.value=True    #Annonce que la queue est à jour (contient les prix)
        Exchange=0.0    #Réinitialise le nombre d'échanges (Achats+Ventes)
        for i in tab:
            Exchange+=i[1]  #Additionne tous les échanges (Achats+Ventes)

        try :
            moy_exchange=Exchange/size  #Calcul la moyenne des échanges du tour
        except:
            moy_exchange=0

def Clock(clock_ok,):
    c=0
    while c<nmbTour:                    #Tant qu'on a pas fait tous les tours :
        clock_ok.set()                  #Lance un top
        c+=1                            #Incrément le compteur
        temps=time.time()
        while time.time()-temps<delai:  #Attend le delai définit avant de recommencer
            time.sleep(2)
        print("**********************************")


def Weather(temp,wind,clock_ok,weather_ok):
    temp[0] = alpha #coef influence temperature
    wind[0] = beta  #coef influence vent
    while clock_ok.wait(1.5*delai): #Attend le top au maximum pendant 1.5 fois le delai
        temp[1]=round(random.gauss(10.0,5.0),2)    #Température au tour actuel (99% entre -5 et 25 degrés)
        wind[1]=round(random.gauss(20.0,5.0),2)    #Vent au tour actuel (99% entre 5.0 et 35.0 km/h)

        temp[1]=1/((temp[1]+6.0)/(18.0+6.0)) #On ne veut que des valeurs positives (donc +6) et on estime qu'une température <= à 18°C est idéal pour la consommation
        wind[1]=(wind[1])/20.0  #On estime qu'un vent soufflant à plus de 43.0km/h est idéal pour la production
        weather_ok.set()    #Prête
        time.sleep(delai/2) #Attend un certain délai (tant que la clock soit passé à False)


def External(p_id):
    Events=[]
    event=False
    if event:
        os.kill(p_id,signal.SIGTERM)

    os.kill(os.getpgid(),signal.SIGINT)



if __name__=="__main__":
    ti=time.time()
    lockQueue = Lock()
    lockCount=Lock()
    lockWrite=Lock()


    queue=Queue()

    clock_ok=Event()
    weather_ok=Event()

    count=Value('i',0)
    temp=Array('f',range(2))
    wind=Array('f',range(2))
    market_OK=Value('b',False)




    Homes=[]

    for i in range(1,nmbHome+1):
        num_policy=random.randrange(1,4)
        h=Process(target=Home, args=(i,lockQueue,lockCount,queue,count,market_OK,lockWrite,clock_ok,temp,wind,weather_ok,num_policy),)
        h.start()
        print("Id",i,"num",num_policy)
        Homes.append(h)

    m=Process(target=Market, args=(queue,count,market_OK,clock_ok,temp,wind))
    m.start()

    w=Process(target=Weather,args=(temp,wind,clock_ok,weather_ok))
    w.start()

    c = Process(target=Clock, args=(clock_ok,))
    c.start()

    c.join()
    m.join()
    w.join()

    for h in Homes:
        h.join()

    print("temps de la simulation:",time.time()-ti)






