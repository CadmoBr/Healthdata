select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select sk_municipality
from "healthdata_dw"."dw_gold"."dim_municipality"
where sk_municipality is null



      
    ) dbt_internal_test